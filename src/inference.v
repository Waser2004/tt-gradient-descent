/*
 * Copyright (c) 2024 Nico Waser
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module inference (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               enable,
    input  wire [7:0]         ui_in,
    input  wire signed [10:0] w,
    input  wire signed [10:0] b,
    output reg  [7:0]         uo_out
);

    wire [5:0] x_value = ui_in[5:0];
    wire signed [16:0] mul_fp = w * $signed({1'b0, x_value});
    wire signed [16:0] b_ext = {{6{b[10]}}, b};
    wire signed [16:0] pred_sum = (mul_fp >>> 4) + b_ext;
    wire signed [11:0] pred_fp = pred_sum[11:0];
    wire signed [7:0] pred_int = $signed(pred_fp[11:4]);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            uo_out <= 8'h00;
        end else if (enable) begin
            uo_out <= pred_int[7:0];
        end else begin
            uo_out <= 8'h00;
        end
    end

endmodule

