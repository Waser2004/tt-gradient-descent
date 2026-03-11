/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_linear_model (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // linear model weigth and bias
  reg signed [3:0] w = 4'b0001;
  reg signed [7:0] b = 4'b0001;

  // forward pass
  wire signed [3:0] x    = ui_in[3:0];
  wire signed [7:0] mult = w * x;
  wire signed [7:0] sum  = mult + b;

  // outputs
  assign uo_out  = sum;
  assign uio_out = sum; // unused output
  assign uio_oe  = sum; // unused output

endmodule
