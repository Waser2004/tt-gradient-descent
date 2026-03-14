![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# Gradient Descent on Tiny Tapeout

This project implements a tiny hardware learning system on Tiny Tapeout.
It can:

- load 5 training samples `(x, y)`
- train a linear model on-chip with gradient descent
- use the trained model to predict outputs for new inputs

The model is:

`y = w * x + b`

The chip stores the training samples internally, updates `w` and `b` during the
training phase, and then enters inference mode automatically.

## Operation

The design moves through three phases:

1. `LOAD_DATA`
   Five training pairs are loaded through the `ui` pins.
2. `TRAIN`
   The internal trainer runs gradient descent for up to 64 steps, or stops early
   if the loss is already low enough.
3. `INFERENCE`
   New input values are applied and the predicted output is returned on `uo[7:0]`.

Pin usage:

- `ui[5:0]`: 6-bit data input
- `ui[6]`: toggle used while loading `(x, y)` samples
- `ui[7]`: enter loading mode, and later return from inference to idle
- `uo[7:0]`: debug output during loading/training, prediction during inference

## Example use

A simple dataset you can load is:

- `(2, 5)`
- `(4, 9)`
- `(6, 13)`
- `(8, 17)`
- `(10, 21)`

This corresponds approximately to:

`y = 2x + 1`

After training, trying values such as `x = 3`, `x = 7`, or `x = 12` should give
outputs close to `7`, `15`, and `25`.

## Testing the chip

For the full hardware procedure, see [docs/info.md](/D:/OneDrive%20-%20Venusnet/Dokumente/2.%20ETHz%C3%BCrich/FS26/tt-gradient-descent/docs/info.md).

In short:

1. Reset the chip.
2. Raise `ui[7]` for one cycle to enter load mode.
3. Load 5 `(x, y)` pairs using `ui[5:0]` and toggle `ui[6]`.
4. Wait for the chip to finish training and enter inference mode.
5. Apply new values on `ui[5:0]` and read the prediction on `uo[7:0]`.

## Local verification

The cocotb testbench covers:

- reset behavior
- full load -> train -> inference flow
- early-stop training behavior

Run it locally with:

```sh
docker compose run --rm test
```
