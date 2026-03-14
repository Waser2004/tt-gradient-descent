/*
 * Copyright (c) 2024 Nico Waser
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_linear_model (
    input  wire [7:0] ui_in,
    output reg  [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    // tie off unused I/O
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

    // FSM states definition
    localparam IDLE      = 2'b00;
    localparam LOAD_DATA = 2'b01;
    localparam TRAIN     = 2'b10;
    localparam INFERENCE = 2'b11;

    reg [1:0] state;

    wire start_load = ui_in[7];

    // training data storage
    reg [5:0] train_x [0:4];
    reg [5:0] train_y [0:4];

    // loader signals
    wire write_x_en;
    wire write_y_en;
    wire [2:0] write_index;
    wire [5:0] write_x;
    wire [5:0] write_y;
    wire load_done;
    wire [2:0] data_index;

    data_loader loader (
        .clk(clk),
        .rst_n(rst_n),
        .ui_in(ui_in),
        .enable(state == LOAD_DATA),

        .write_x_en(write_x_en),
        .write_y_en(write_y_en),
        .write_index(write_index),
        .write_x(write_x),
        .write_y(write_y),
        .load_done(load_done),
        .data_index(data_index)
    );

    // trainer signals
    wire signed [10:0] w; // 7 bits for value + 4 bits for fraction
    wire signed [10:0] b; // 7 bits for value + 4 bits for fraction
    wire [6:0] train_step;
    wire train_done;
    wire [7:0] inference_out;
    wire [29:0] train_x_flat;
    wire [29:0] train_y_flat;

    assign train_x_flat = {train_x[4], train_x[3], train_x[2], train_x[1], train_x[0]};
    assign train_y_flat = {train_y[4], train_y[3], train_y[2], train_y[1], train_y[0]};

    trainer trainer (
        .clk(clk),
        .rst_n(rst_n),
        .enable(state == TRAIN),
        .train_x_flat(train_x_flat),
        .train_y_flat(train_y_flat),

        .w(w),
        .b(b),
        .train_step(train_step),
        .train_done(train_done)
    );

    inference inference (
        .clk(clk),
        .rst_n(rst_n),
        .enable(state == INFERENCE),
        .ui_in(ui_in),
        .w(w),
        .b(b),
        .uo_out(inference_out)
    );

    // FSM
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= IDLE;
        else begin
            case (state)

                IDLE:
                    if (start_load)
                        state <= LOAD_DATA;

                LOAD_DATA:
                    if (load_done)
                        state <= TRAIN;

                TRAIN:
                    if (train_done)
                        state <= INFERENCE;

                INFERENCE:
                    if (ui_in[7] == 1'b1)
                        state <= IDLE;

            endcase
        end
    end

    // memory writes
    always @(posedge clk) begin
        if (write_x_en)
            train_x[write_index] <= write_x;

        if (write_y_en)
            train_y[write_index] <= write_y;
    end

    // debug output
    always @(*) begin
        if (state == INFERENCE) begin
            uo_out = inference_out;
        end else begin
            uo_out[7:6] = state;
            uo_out[2:0] = write_index;
            uo_out[5:3] = 3'b000;
        end
    end

    wire _unused = &{ena, uio_in};

endmodule
