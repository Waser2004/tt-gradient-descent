/*
 * Copyright (c) 2024 Nico Waser
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module inference (
    input  wire               enable,
    input  wire [7:0]         ui_in,
    input  wire signed [10:0] w,
    input  wire signed [10:0] b,
    output wire [7:0]         uo_out
);

    wire [5:0] x_value = ui_in[5:0];
    wire signed [16:0] mul_fp = w * $signed({1'b0, x_value});
    wire signed [11:0] pred_fp = (mul_fp >>> 4) + b;
    wire signed [7:0] pred_int = pred_fp >>> 4;

    assign uo_out = enable ? pred_int[7:0] : 8'h00;

endmodule

