# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

# Define FSM states as constants for readability
IDLE      = 0b00
LOAD_DATA = 0b01
TRAIN     = 0b10
INFERENCE = 0b11


async def reset_dut(dut):
    dut._log.info("Reset DUT")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)


def set_bit(value: int, bit: int, bit_value: int) -> int:
    if bit_value:
        return value | (1 << bit)
    return value & ~(1 << bit)


async def load_sample(dut, x: int, y: int):
    """
    Protocol:
    - rising edge of ui_in[6] stores x = ui_in[3:0]
    - falling edge of ui_in[6] schedules y write into loader register
    - the top-level memory captures that value one clock later
    """

    # Put x on lower nibble, keep start_load high on bit 7, toggle bit low first
    ui_val = 0
    ui_val = set_bit(ui_val, 7, 1)          # keep start_load asserted
    ui_val = set_bit(ui_val, 6, 0)          # toggle low
    ui_val = (ui_val & 0b11110000) | (x & 0xF)
    dut.ui_in.value = ui_val
    await ClockCycles(dut.clk, 1)

    # Rising edge on bit 6 -> store x
    ui_val = set_bit(ui_val, 6, 1)
    dut.ui_in.value = ui_val
    await ClockCycles(dut.clk, 1)

    # Put y on full byte, but keep bit 6 high for now
    # Note: this means bit 7 may no longer be "start_load" during the y phase.
    # That is okay because the FSM is already in LOAD_DATA.
    ui_val = y & 0xFF
    ui_val = set_bit(ui_val, 6, 1)
    dut.ui_in.value = ui_val
    await ClockCycles(dut.clk, 1)

    # Falling edge on bit 6 -> store y
    ui_val = set_bit(ui_val, 6, 0)
    dut.ui_in.value = ui_val
    await ClockCycles(dut.clk, 1)

    # `project.v` writes train_y on the cycle after loader asserts write_y_en.
    await ClockCycles(dut.clk, 1)


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

@cocotb.test()
async def test_reset_state(dut):
    dut._log.info("Start reset-state test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    uo_out = dut.uo_out.value.to_unsigned()
    state = (uo_out >> 6) & 0b11
    index = dut.user_project.loader.data_index.value.to_unsigned()

    dut._log.info(f"After reset: uo_out={uo_out:08b}")
    assert state == IDLE, f"Expected IDLE after reset, got state={state}"
    assert index == 0, f"Expected index 0 after reset, got index={index}"


@cocotb.test()
async def test_enter_load_data(dut):
    dut._log.info("Start enter-load-data test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # start_load = ui_in[7] = 1 and then 0 should transition FSM to LOAD_DATA
    dut.ui_in.value = 0b10000000
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0b00000000
    await ClockCycles(dut.clk, 1)

    uo_out = dut.uo_out.value.to_unsigned()
    state = (uo_out >> 6) & 0b11
    dut._log.info(f"After start_load: uo_out={uo_out:08b}")
    assert state == LOAD_DATA, f"Expected LOAD_DATA, got state={state}"


@cocotb.test()
async def test_load_one_sample(dut):
    dut._log.info("Start single-sample load test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # start_load = ui_in[7] = 1 and then 0 should transition FSM to LOAD_DATA
    dut.ui_in.value = 0b10000000
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0b00000000
    await ClockCycles(dut.clk, 1)

    state = (dut.uo_out.value.to_unsigned() >> 6) & 0b11
    assert state == LOAD_DATA, "FSM did not enter LOAD_DATA"

    # Load one sample: x=3, y=5
    await load_sample(dut, x=3, y=5)

    # One extra cycle avoids sampling during the write handoff.
    await ClockCycles(dut.clk, 1)

    # Check stored values in top-level memories
    train_x0 = dut.user_project.train_x[0].value.to_signed()
    train_y0 = dut.user_project.train_y[0].value.to_signed()

    dut._log.info(f"train_x[0]={train_x0}, train_y[0]={train_y0}")
    assert train_x0 == 3, f"Expected train_x[0] = 3, got {train_x0}"
    assert train_y0 == 5, f"Expected train_y[0] = 5, got {train_y0}"

    # Read the actual next sample index from the data_loader instance.
    uo_out = dut.uo_out.value.to_unsigned()
    index = dut.user_project.loader.data_index.value.to_unsigned()
    dut._log.info(f"uo_out={uo_out:08b}, data_index={index}")
    assert index == 1, f"Expected write_index = 1 after one sample, got {index}"


@cocotb.test()
async def test_load_five_samples_and_finish(dut):
    dut._log.info("Start five-sample load test")

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Enter load mode
    dut.ui_in.value = 0b10000000
    await ClockCycles(dut.clk, 1)

    samples = [
        (1, 2),
        (2, 4),
        (3, 6),
        (4, 8),
        (5, 10),  # stored as signed in RTL, driven as raw bits
    ]

    for x_raw, y_raw in samples:
        await load_sample(dut, x=x_raw, y=y_raw)
        dut._log.info(f"data_index after sample: {dut.user_project.loader.data_index.value.to_unsigned()} output index in uo_out: {dut.uo_out.value.to_unsigned() & 0b111}")

    # Give FSM one cycle to react to load_done and return to IDLE
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 2)

    # Check memory contents
    expected_x = [1, 2, 3, 4, 5]
    # ui_in[4] is the loader toggle, so the stored y always has bit 4 = 0.
    expected_y = [2, 4, 6, 8, 10]

    for i in range(5):
        actual_x = dut.user_project.train_x[i].value.to_signed()
        actual_y = dut.user_project.train_y[i].value.to_signed()
        dut._log.info(f"sample[{i}] -> x={actual_x}, y={actual_y}")
        assert actual_x == expected_x[i], f"train_x[{i}] expected {expected_x[i]}, got {actual_x}"
        assert actual_y == expected_y[i], f"train_y[{i}] expected {expected_y[i]}, got {actual_y}"

    # FSM should be back in IDLE
    uo_out = dut.uo_out.value.to_unsigned()
    state = (uo_out >> 6) & 0b11
    index = dut.user_project.loader.data_index.value.to_unsigned()

    dut._log.info(f"Final uo_out={uo_out:08b}")
    assert state == TRAIN, f"Expected TRAIN after 5 samples, got state={state}"
    assert index == 0, f"Expected index reset to 0 after completion, got index={index}"