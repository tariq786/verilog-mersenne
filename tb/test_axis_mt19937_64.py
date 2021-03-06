#!/usr/bin/env python2
"""

Copyright (c) 2014 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

from myhdl import *
import os
from Queue import Queue

import axis_ep
import mt19937_64

module = 'axis_mt19937_64'

srcs = []

srcs.append("../rtl/%s.v" % module)
srcs.append("test_%s.v" % module)

src = ' '.join(srcs)

build_cmd = "iverilog -o test_%s.vvp %s" % (module, src)

def dut_axis_mt19937_64(clk,
                        rst,
                        current_test,

                        output_axis_tdata,
                        output_axis_tvalid,
                        output_axis_tready,

                        seed_val,
                        seed_start,

                        busy):

    if os.system(build_cmd):
        raise Exception("Error running build command")
    return Cosimulation("vvp -m myhdl test_%s.vvp -lxt2" % module,
                clk=clk,
                rst=rst,
                current_test=current_test,

                output_axis_tdata=output_axis_tdata,
                output_axis_tvalid=output_axis_tvalid,
                output_axis_tready=output_axis_tready,

                seed_val=seed_val,
                seed_start=seed_start,

                busy=busy)

def bench():

    # Inputs
    clk = Signal(bool(0))
    rst = Signal(bool(0))
    current_test = Signal(intbv(0)[8:])

    seed_val = Signal(intbv(0)[64:])
    seed_start = Signal(bool(0))
    output_axis_tready = Signal(bool(0))

    # Outputs
    output_axis_tdata = Signal(intbv(0)[64:])
    output_axis_tvalid = Signal(bool(0))
    busy = Signal(bool(0))

    # sources and sinks
    sink_queue = Queue()
    sink_pause = Signal(bool(0))

    sink = axis_ep.AXIStreamSink(clk,
                                 rst,
                                 tdata=output_axis_tdata,
                                 tvalid=output_axis_tvalid,
                                 tready=output_axis_tready,
                                 fifo=sink_queue,
                                 pause=sink_pause,
                                 name='sink')

    # DUT
    dut = dut_axis_mt19937_64(clk,
                           rst,
                           current_test,

                           output_axis_tdata,
                           output_axis_tvalid,
                           output_axis_tready,

                           seed_val,
                           seed_start,

                           busy)

    @always(delay(4))
    def clkgen():
        clk.next = not clk

    @instance
    def check():
        yield delay(100)
        yield clk.posedge
        rst.next = 1
        yield clk.posedge
        rst.next = 0
        yield clk.posedge
        yield delay(100)
        yield clk.posedge

        yield clk.posedge

        yield output_axis_tvalid.posedge

        mt = mt19937_64.mt19937_64()

        print("test 1: check 1000 values")
        current_test.next = 1

        for i in range(1000):
            while sink_queue.empty():
                yield clk.posedge

            frame = sink_queue.get()
            assert frame.data[0] == mt.int64()

        print("test 2: pause sink")
        current_test.next = 2

        for i in range(100):
            sink_pause.next = True
            yield clk.posedge
            yield clk.posedge
            yield clk.posedge
            sink_pause.next = False
            yield clk.posedge

        for i in range(1000):
            while sink_queue.empty():
                yield clk.posedge

            frame = sink_queue.get()
            assert frame.data[0] == mt.int64()

        yield delay(100)

        print("test 3: new seed")
        current_test.next = 3

        mt.seed(0x1234567812345678)

        yield clk.posedge
        seed_val.next = 0x1234567812345678
        seed_start.next = 1
        yield clk.posedge
        seed_start.next = 0
        yield clk.posedge

        while not sink_queue.empty():
            sink_queue.get()

        for i in range(1000):
            while sink_queue.empty():
                yield clk.posedge

            frame = sink_queue.get()
            assert frame.data[0] == mt.int64()

        raise StopSimulation

    return dut, sink, clkgen, check

def test_bench():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sim = Simulation(bench())
    sim.run()

if __name__ == '__main__':
    print("Running test...")
    test_bench()

