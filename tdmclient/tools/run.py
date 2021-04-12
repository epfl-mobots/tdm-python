# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import sys
import os
import getopt

from tdmclient import ClientAsync
from tdmclient.atranspiler import ATranspiler


def help():
    print("""Usage: python3 -m tdmclient.tools.run [options] [filename]
Run program on robot, from file or stdin

Options:
  --debug n    display diagnostic information (0=none, 1=basic, 2=more, 3=verbose)
  --help       display this help message and exit
  --language=L programming language (aseba or python); default=automatic
  --scratchpad also store program into the TDM scratchpad
  --sponly     store program into the TDM without running it
  --stop       stop program (no filename or stdin expected)
  --tdmaddr=H  tdm address (default: localhost or from zeroconf)
  --tdmport=P  tdm port (default: from zeroconf)
""")


if __name__ == "__main__":

    debug = 0
    language = None  # auto
    stop = False
    scratchpad = 0  # 1=--scratchpad, 2=--sponly
    tdm_addr = None
    tdm_port = None

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "debug=",
                                              "help",
                                              "language=",
                                              "scratchpad",
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
        elif arg == "--language":
            language = val
        elif arg == "--scratchpad":
            scratchpad = 1
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

    with ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port, debug=debug) as client:

        async def prog():
            global status
            with await client.lock() as node:
                if stop:
                    error = await node.stop()
                    if error is not None:
                        print(f"Stop error {error['error_code']}")
                        status = 2
                else:
                    if scratchpad < 2:
                        error = await node.compile(program)
                        if error is not None:
                            print(f"Compilation error: {error['error_msg']}")
                            status = 2
                        else:
                            error = await node.run()
                            if error is not None:
                                print(f"Run error {error['error_code']}")
                                status = 2
                    if scratchpad > 0:
                        error = await node.set_scratchpad(program)
                        if error is not None:
                            print(f"Scratchpad error {error['error_code']}")
                            status = 2

        client.run_async_program(prog)

    sys.exit(status)
