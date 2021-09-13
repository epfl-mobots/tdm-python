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
from tdmclient.module_thymio import ModuleThymio


def help(**kwargs):
    print("""Usage: python3 -m tdmclient.tools.run [options] [filename]
Run program on robot, from file or stdin

Options:
  --debug n      display diagnostic information (0=none, 1=basic, 2=more, 3=verbose)
  --help         display this help message and exit
  --language=L   programming language (aseba or python); default=automatic
  --nosleep      exit immediately (default with neither events nor print statement)
  --nothymio     don't import the symbols of thymio library
  --robotid=I    robot id; default=any
  --robotname=N  robot name; default=any
  --scratchpad   also store program into the TDM scratchpad
  --sleep        sleep forever (default with events or print statement)
  --sponly       store program into the TDM without running it
  --stop         stop program (no filename or stdin expected)
  --tdmaddr=H    tdm address (default: localhost or from zeroconf)
  --tdmport=P    tdm port (default: from zeroconf)
""", **kwargs)


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
    import_thymio = True

    print_statements = []
    exit_received = None  # or exit status once received

    def on_event_received(node, event_name, event_data):
        if event_name == "_exit":
            global exit_received
            exit_received = event_data[0]
        elif event_name == "_print":
            print_id = event_data[0]
            print_format, print_num_args = print_statements[print_id]
            print_args = tuple(event_data[1 : 1 + print_num_args])
            print_str = print_format % print_args
            print(print_str)
        else:
            print(event_name + "".join(["," + str(d) for d in event_data]))

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "debug=",
                                              "event=",
                                              "help",
                                              "language=",
                                              "nosleep",
                                              "nothymio",
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
        print(str(err), file=sys.stderr)
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
                help(file=sys.stderr)
                sys.exit(1)
            events.append((
                r.group(1),
                0 if r.group(3) is None else int(r.group(3)),
            ))
        elif arg == "--language":
            language = val
        elif arg == "--nosleep":
            sleep = False
        elif arg == "--nothymio":
            import_thymio = False
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
            help(file=sys.stderr)
            sys.exit(1)
    else:
        if len(values) == 0:
            program = sys.stdin.read()
            if language is None:
                # try to transpile code from Python
                try:
                    transpiler = ATranspiler()
                    if import_thymio:
                        transpiler.set_preamble("""from thymio import *
""")
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
            help(file=sys.stderr)
            sys.exit(1)

    status = 0

    if language == "python":
        # transpile from Python to Aseba
        modules = {
            "thymio": ModuleThymio()
        }
        transpiler = ATranspiler()
        transpiler.modules = {**transpiler.modules, **modules}
        if import_thymio:
            transpiler.set_preamble("""from thymio import *
""")
        transpiler.set_source(program)
        transpiler.transpile()
        program = transpiler.get_output()
        print_statements = transpiler.print_format_strings
        if len(print_statements) > 0:
            events.append(("_print", 1 + transpiler.print_max_num_args))
        if transpiler.has_exit_event:
            events.append(("_exit", 1))
        for event_name in transpiler.events:
            events.append((event_name, transpiler.events[event_name]))

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
                        # expect events: wait forever or until _exit is received
                        def wake():
                            return exit_received is not None
                        await client.sleep(-1, wake)
                        await node.stop()
                        status = exit_received

        client.run_async_program(prog)

    sys.exit(status)
