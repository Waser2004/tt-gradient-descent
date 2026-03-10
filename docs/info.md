<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project implements a tiny **linear regression model in hardware**.

The model computes a prediction using the equation:

ŷ = w · x + b

Where:
- `x` is the input value provided on `ui_in`
- `w` is the model weight stored in a register
- `b` is the bias stored in a register
- `ŷ` is the predicted output

The chip trains the parameters `w` and `b` using **gradient descent** on a small dataset stored on-chip.  
For each training sample the chip:

1. Computes the prediction `ŷ = w·x + b`
2. Calculates the error `e = ŷ − y`
3. Updates the parameters using gradient descent

w ← w − η(e·x)  
b ← b − ηe

After training finishes, the chip can compute predictions for new input values.

All numbers are represented as **signed two's complement integers**.


## How to test

1. Power the Tiny Tapeout board with the design loaded.

2. Provide an input value `x` on the input pins `ui_in`.

3. The chip computes the prediction using the trained model:

   ŷ = w · x + b

4. The predicted value `ŷ` is output on `uo_out`.

Try different input values to observe how the output changes according to the learned linear relationship.


## External hardware

None.