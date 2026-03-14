# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


IDLE = 0b00
LOAD_DATA = 0b01
TRAIN = 0b10
INFERENCE = 0b11


def s(value: int, bits: int) -> int:
    mask = (1 << bits) - 1
    value &= mask
    sign = 1 << (bits - 1)
    return value - (1 << bits) if (value & sign) else value


def inference_reference(w: int, b: int, x_raw: int) -> int:
    x = x_raw & 0x3F
    pred_fp = s(((s(w, 11) * x) >> 4) + s(b, 11), 12)
    pred_int = s(pred_fp >> 4, 8)
    return pred_int & 0xFF


async def reset_dut(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)


def state(dut) -> int:
    return dut.user_project.state.value.to_unsigned()


async def enter_load_mode(dut):
    dut.ui_in.value = 0b10000000
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1)


async def load_sample(dut, x: int, y: int):
    # Toggle low with x value and start_load high.
    ui = (1 << 7) | (x & 0x3F)
    ui &= ~(1 << 6)
    dut.ui_in.value = ui
    await ClockCycles(dut.clk, 1)

    # Toggle rise -> write x.
    dut.ui_in.value = ui | (1 << 6)
    await ClockCycles(dut.clk, 1)

    # Put y and keep toggle high.
    ui = (y & 0x3F) | (1 << 6)
    dut.ui_in.value = ui
    await ClockCycles(dut.clk, 1)

    # Toggle fall -> write y.
    dut.ui_in.value = ui & ~(1 << 6)
    await ClockCycles(dut.clk, 1)

    # Top-level memory updates one cycle later.
    await ClockCycles(dut.clk, 1)


async def wait_for_state(dut, target_state: int, timeout_cycles: int):
    for _ in range(timeout_cycles):
        if state(dut) == target_state:
            return
        await ClockCycles(dut.clk, 1)
    assert False, f"Timeout waiting for state={target_state}, current={state(dut)}"


async def capture_training_done(dut, max_cycles: int = 80):
    saw_done = False
    done_step = 0
    done_loss = 0

    for _ in range(max_cycles):
        cur_state = state(dut)
        if cur_state == TRAIN and dut.user_project.train_done.value == 1:
            saw_done = True
            done_step = dut.user_project.train_step.value.to_unsigned()
            done_loss = dut.user_project.trainer.loss.value.to_signed()

        if cur_state == INFERENCE:
            break

        await ClockCycles(dut.clk, 1)

    assert state(dut) == INFERENCE, f"Expected INFERENCE, got {state(dut)}"
    return saw_done, done_step, done_loss


@cocotb.test()
async def test_reset_state(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    await reset_dut(dut)

    assert state(dut) == IDLE
    assert dut.user_project.train_step.value.to_unsigned() == 0
    assert dut.user_project.train_done.value == 0
    assert dut.user_project.w.value.to_signed() == 0
    assert dut.user_project.b.value.to_signed() == 0


@cocotb.test()
async def test_full_system_load_train_infer(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    await reset_dut(dut)

    samples = [
        (2, 5),
        (4, 9),
        (6, 13),
        (8, 17),
        (10, 21),
    ]

    await enter_load_mode(dut)
    assert state(dut) == LOAD_DATA

    for x, y in samples:
        await load_sample(dut, x, y)

    dut.ui_in.value = 0
    await wait_for_state(dut, TRAIN, timeout_cycles=10)

    saw_done, done_step, done_loss = await capture_training_done(dut)

    actual_w = dut.user_project.w.value.to_signed()
    actual_b = dut.user_project.b.value.to_signed()
    assert saw_done, "Expected train_done pulse during TRAIN state"

    # Golden reference for this dataset with current fixed-point RTL.
    expected_w = -884
    expected_b = 146
    assert actual_w == expected_w, f"Expected w={expected_w}, got {actual_w}"
    assert actual_b == expected_b, f"Expected b={expected_b}, got {actual_b}"

    # Training can stop early on low loss, or after 64 steps.
    assert 1 <= done_step <= 64, f"Unexpected done_step={done_step}"
    if done_step < 64:
        assert done_loss < 0x0010, (
            f"Early stop requires low loss, got loss={done_loss}, step={done_step}"
        )
    else:
        assert done_step == 64

    # Verify inference outputs for several inputs.
    for x_in in (0, 3, 7, 12, 31, 63):
        dut.ui_in.value = x_in & 0x3F
        await ClockCycles(dut.clk, 1)
        got = dut.uo_out.value.to_unsigned()
        expected = inference_reference(actual_w, actual_b, x_in)
        assert got == expected, f"Inference mismatch for x={x_in}: got {got}, expected {expected}"

    # Return to IDLE from INFERENCE using ui_in[7].
    dut.ui_in.value = 0b10000000
    await ClockCycles(dut.clk, 1)
    await wait_for_state(dut, IDLE, timeout_cycles=3)

    # trainer reset behavior outside TRAIN state.
    await ClockCycles(dut.clk, 1)
    assert dut.user_project.train_step.value.to_unsigned() == 0
    assert dut.user_project.train_done.value == 0


@cocotb.test()
async def test_training_early_stop_on_perfect_fit(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    await reset_dut(dut)

    # Perfect-fit dataset for initial model (w=0, b=0) => zero error on first epoch.
    samples = [
        (1, 0),
        (7, 0),
        (15, 0),
        (31, 0),
        (63, 0),
    ]

    await enter_load_mode(dut)
    assert state(dut) == LOAD_DATA

    for x, y in samples:
        await load_sample(dut, x, y)

    dut.ui_in.value = 0
    await wait_for_state(dut, TRAIN, timeout_cycles=10)
    saw_done, done_step, done_loss = await capture_training_done(dut, max_cycles=10)

    # Must stop because loss is already below threshold (not because of max-step timeout).
    assert saw_done, "Expected train_done pulse during TRAIN state"
    assert done_step == 1, f"Expected early-stop at step 1, got step {done_step}"
    assert done_loss == 0, f"Expected zero loss for perfect-fit dataset, got {done_loss}"

    # Parameters should remain unchanged for zero-gradient data.
    assert dut.user_project.w.value.to_signed() == 0
    assert dut.user_project.b.value.to_signed() == 0

    # Inference should output 0 for any input with w=b=0.
    for x_in in (0, 5, 19, 42, 63):
        dut.ui_in.value = x_in & 0x3F
        await ClockCycles(dut.clk, 1)
        assert dut.uo_out.value.to_unsigned() == 0, f"Expected 0 output for x={x_in}"
