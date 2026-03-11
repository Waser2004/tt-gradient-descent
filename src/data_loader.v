/*
 * Copyright (c) 2024 Nico Waser
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module data_loader (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] ui_in,
    input  wire       enable,

    output reg        write_x_en,
    output reg        write_y_en,
    output reg  [2:0] write_index,
    output reg signed [3:0] write_x,
    output reg signed [7:0] write_y,
    output reg        load_done
);

    reg prev_toggle;
    reg [2:0] data_index;

    wire rise;
    wire fall;

    assign rise = (prev_toggle == 1'b0) && (ui_in[4] == 1'b1);
    assign fall = (prev_toggle == 1'b1) && (ui_in[4] == 1'b0);

    always @(posedge clk or negedge rst_n) begin
        // reset all signals on reset
        if (!rst_n) begin
            prev_toggle <= 0;
            data_index  <= 0;
            write_x_en  <= 0;
            write_y_en  <= 0;
            write_index <= 0;
            write_x     <= 0;
            write_y     <= 0;
            load_done   <= 0;

        // main logic
        end else begin
            prev_toggle <= ui_in[4];

            write_x_en <= 0;
            write_y_en <= 0;
            load_done  <= 0;

            if (enable) begin
                // on rising edge of toggle, write x;
                if (rise) begin
                    write_x_en  <= 1;
                    write_index <= data_index;
                    write_x     <= ui_in[3:0];
                end
                
                // on falling edge, write y; after 5 pairs of (x,y) are loaded, set load_done
                if (fall) begin
                    write_y_en  <= 1;
                    write_index <= data_index;
                    write_y     <= ui_in;

                    if (data_index == 3'd4) begin
                        data_index <= 0;
                        load_done  <= 1;
                    end else begin
                        data_index <= data_index + 1;
                    end
                end

            end else begin
                data_index <= 0;
                write_index <= 0;
            end
        end
    end

endmodule