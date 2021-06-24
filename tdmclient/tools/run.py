# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import sys
import os
import getopt
import re

from tdmclient import ClientAsync
from tdmclient.atranspiler import ATranspiler


def help():
    print("""Usage: python3 -m tdmclient.tools.run [options] [filename]
Run program on robot, from file or stdin

Options:
  --debug n      display diagnostic information (0=none, 1=basic, 2=more, 3=verbose)
  --help         display this help message and exit
  --language=L   programming language (aseba or python); default=automatic
  --nosleep      exit immediately (default with neither events nor print statement)
  --robotid=I    robot id; default=any
  --robotname=N  robot name; default=any
  --scratchpad   also store program into the TDM scratchpad
  --sleep        sleep forever (default with events or print statement)
  --sponly       store program into the TDM without running it
  --stop         stop program (no filename or stdin expected)
  --tdmaddr=H    tdm address (default: localhost or from zeroconf)
  --tdmport=P    tdm port (default: from zeroconf)
""")


if __name__ == "__main__":

    debug = 0
    language = None  # auto
    stop = False
    scratchpad = 0  # 1=--scratchpad, 2=--sponly
    tdm_addr = None
    tdm_port = None
    robot_id = None
    robot_name = None
    events = []
    event_re = re.compile(r"^([^[]*)(\[([0-9]]*)\])?")
    sleep = None  # True to sleep forever, False to exit immediately

    def on_event_received(node, event_name, event_data):
        print("event", event_name, event_data)

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "debug=",
                                              "event=",
                                              "help",
                                              "language=",
                                              "nosleep",
                                              "robotid=",
                                              "robotname=",
                                              "scratchpad",
                                              "sleep",
                                              "sponly",
                                              "stop",
                                              "tdmaddr=",
                                              "tdmport=",
                                          ])
    except getopt.error as err:
        print(str(err))
        sys.exit(1)
    for arg, val in arguments:
        if arg == "--help":
            help()
            sys.exit(0)
        elif arg == "--debug":
            debug = int(val)
        elif arg == "--event":
            r = event_re.match(val)
            if r is None:
                help()
                sys.exit(1)
            events.append((
                r.group(1),
                0 if r.group(3) is None else int(r.group(3)),
            ))
        elif arg == "--language":
            language = val
        elif arg == "--nosleep":
            sleep = False
        elif arg == "--robotid":
            robot_id = val
        elif arg == "--robotname":
            robot_name = val
        elif arg == "--scratchpad":
            scratchpad = 1
        elif arg == "--sleep":
            sleep = True
        elif arg == "--sponly":
            scratchpad = 2
        elif arg == "--stop":
            stop = True
        elif arg == "--tdmaddr":
            tdm_addr = val
        elif arg == "--tdmport":
            tdm_port = int(val)

    if stop:
        if len(values) > 0:
            help()
            sys.exit(1)
    else:
        if len(values) == 0:
            program = sys.stdin.read()
            if language is None:
                # try to transpile code from Python
                try:
                    transpiler = ATranspiler()
                    transpiler.set_source(program)
                    transpiler.transpile()
                    # successful, must be Python
                    language = "python"
                except:
                    # failure, assume Aseba
                    language = "aseba"
        elif len(values) == 1:
            with open(values[0]) as f:
                program = f.read()
            if language is None:
                # guess language from file extension
                language = "python" if os.path.splitext(values[0])[1] == ".py" else "aseba"
        else:
            help()
            sys.exit(1)

    status = 0

    if language == "python":
        # transpile from Python to Aseba
        program = ATranspiler.simple_transpile(program)

    if sleep is None:
        sleep = len(events) > 0

    with ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port, debug=debug) as client:

        async def prog():
            global status
            with await client.lock(node_id=robot_id, node_name=robot_name) as node:
                if stop:
                    error = await node.stop()
                    if error is not None:
                        print(f"Stop error {error['error_code']}")
                        status = 2
                else:
                    if scratchpad < 2:
                        if len(events) > 0:
                            await node.register_events(events)
                        error = await node.compile(program)
                        if error is not None:
                            print(f"Compilation error: {error['error_msg']}")
                            status = 2
                        else:
                            if len(events) > 0 and sleep:
                                client.add_event_received_listener(on_event_received)
                                await node.watch(events=True)
                            error = await node.run()
                            if error is not None:
                                print(f"Run error {error['error_code']}")
                                status = 2
                    if scratchpad > 0:
                        error = await node.set_scratchpad(program)
                        if error is not None:
                            print(f"Scratchpad error {error['error_code']}")
                            status = 2
                    if scratchpad < 2 and sleep:
                        # expect events: wait forever
                        await client.sleep(-1)

        client.run_async_program(prog)

    sys.exit(status)
