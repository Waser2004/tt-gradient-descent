## How it works

This project is a small hardware learning system for a linear model.
It stores 5 training samples on-chip, trains a model with gradient descent, and
then uses the trained model to make predictions for new input values.

The design has three operating phases:

1. `LOAD_DATA`
   Load 5 training pairs `(x, y)` into the chip.
2. `TRAIN`
   The chip updates the internal weight `w` and bias `b` with gradient descent.
3. `INFERENCE`
   The chip uses the trained `w` and `b` to compute an output for a new input `x`.

The model equation is:

`y = w * x + b`

Internally, `w` and `b` are stored in fixed-point format.
Training runs automatically after the 5th sample is loaded.
The trainer stops either:

- after 64 training steps, or
- earlier if the loss becomes small enough.

Pin usage:

- `ui[5:0]`: 6-bit value input
- `ui[6]`: load toggle during data entry
- `ui[7]`: start loading, and later reset back to idle from inference
- `uo[7:0]`: output

During `LOAD_DATA`, the output is debug information:

- `uo[7:6]`: current state
- `uo[2:0]`: current write index

State encoding:

- `00` = `IDLE`
- `01` = `LOAD_DATA`
- `10` = `TRAIN`
- `11` = `INFERENCE`

During `INFERENCE`, `uo[7:0]` is the predicted output value.


## How to test

The chip is easiest to test in four stages.

### 1. Reset

- Apply clock and power.
- Hold `rst_n` low, then set it high.
- Keep `ui[7:0] = 0`.
- After reset, the chip is in `IDLE`, so the debug output should show state `00`.

### 2. Load 5 training samples

To enter load mode:

- Set `ui[7] = 1` for one clock cycle.
- Then set `ui[7] = 0`.
- The chip should move to `LOAD_DATA` and `uo[7:6]` should become `01`.

To load one sample `(x, y)`:

1. Put `x` on `ui[5:0]` with `ui[6] = 0`.
2. Toggle `ui[6]` from `0` to `1` for one clock edge.
   This stores `x`.
3. Put `y` on `ui[5:0]` while keeping `ui[6] = 1`.
4. Toggle `ui[6]` from `1` to `0` for one clock edge.
   This stores `y`.

Repeat that for 5 samples.

Example dataset that works well:

- `(2, 5)`
- `(4, 9)`
- `(6, 13)`
- `(8, 17)`
- `(10, 21)`

This dataset represents the line:

`y = 2x + 1`

After the 5th sample, the chip automatically leaves `LOAD_DATA` and starts training.

### 3. Wait for training to finish

- During training, the debug output state is `10`.
- When training is finished, the chip enters `INFERENCE`.
- In `INFERENCE`, the debug output is replaced by the predicted value.

### 4. Run inference

- Put a new 6-bit input value on `ui[5:0]`.
- Keep `ui[7] = 0`.
- Wait at least one clock cycle.
- Read the predicted value on `uo[7:0]`.

With the example dataset above, the output should approximately follow:

- input `x = 3` -> output near `7`
- input `x = 7` -> output near `15`
- input `x = 12` -> output near `25`

To return to `IDLE` and start again:

- Set `ui[7] = 1` for one clock cycle while in `INFERENCE`.


## External hardware

None.
