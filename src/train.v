/*
 * Copyright (c) 2024 Nico Waser
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module trainer (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                enable,
    input  wire [29:0]         train_x_flat,    // 5x6-bit packed x values
    input  wire [29:0]         train_y_flat,    // 5x6-bit packed y values

    output reg signed [10:0]   w,              // 7 bits for value + 4 bits for fraction
    output reg signed [10:0]   b,              // 7 bits for value + 4 bits for fraction
    output reg unsigned [6:0]  train_step,
    output reg                 train_done
);

    reg signed [15:0] loss;   // mean squared error loss (12 bits value + 4 bits fraction)
    reg signed [10:0] w_grad; // 7 bits value + 4 bits fraction
    reg signed [10:0] b_grad; // 7 bits value + 4 bits fraction
    reg signed [10:0] y_pred; // 7 bits value + 4 bits fraction
    reg signed [10:0] error;  // 7 bits value + 4 bits fraction
    reg signed [10:0] y_target_fp;

    always @(posedge clk or negedge rst_n) begin
        // reset all signals on reset
        if (!rst_n) begin
            w           <= 0;
            b           <= 0;
            loss        <= 0;
            train_step  <= 0;
            train_done  <= 0;

        // main logic
        end else begin
            if (enable) begin

                // calculate gradients and update parameters
                loss = 0;
                w_grad = 0;
                b_grad = 0;
                train_done <= 0;

                for (int i = 0; i < 5; i++) begin
                    // forward pass: y_pred = w * x + b (fixed-point multiplication and addition)
                    y_pred = (w * train_x_flat[i*6 +: 6]) >>> 4;
                    y_pred = y_pred + b;
                    
                    // calculate error
                    y_target_fp = $signed({1'b0, train_y_flat[i*6 +: 6], 4'b0000});
                    error = y_pred - y_target_fp;
                    loss  = loss + (error * error) >>> 4; // accumulate loss

                    // accumulate gradients
                    w_grad = w_grad + ((error * train_x_flat[i*6 +: 6]) >>> 4);
                    b_grad = b_grad + error;
                end

                // update parameters with a learning rate of 0.1 (0.0001 in fixed-point)
                w <= w - (w_grad >>> 4);
                b <= b - (b_grad >>> 4);

                // increment training step and update loss
                loss       <= loss / 5;
                train_step <= train_step + 1;

                // after 64 training steps, set train_done or loss is below threshold of  0.01
                if (train_step == 6'd63 || loss < 16'h0010) begin
                    train_done <= 1;
                end

            end else begin
                // Prepare for the next training session once TRAIN state is exited.
                train_step <= 0;
                train_done <= 0;
            end
        end
    end

endmodule

