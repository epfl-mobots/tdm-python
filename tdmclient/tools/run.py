# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import sys
import getopt

from tdmclient import ClientAsync


def help():
    print("""Usage: python3 -m tdmclient.tools.run [options] [filename]
Run program on robot, from file or stdin

Options:
  --debug n    display diagnostic information (0=none, 1=basic, 2=more, 3=verbose)
  --help       display this help message and exit
  --scratchpad also store program into the TDM scratchpad
  --sponly     store program into the TDM without running it
  --stop       stop program (no filename or stdin expected)
""")


if __name__ == "__main__":

    debug = 0
    stop = False
    scratchpad = 0  # 1=--scratchpad, 2=--sponly

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "debug=",
                                              "help",
                                              "scratchpad",
                                              "sponly",
                                              "stop",
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
        elif arg == "--scratchpad":
            scratchpad = 1
        elif arg == "--sponly":
            scratchpad = 2
        elif arg == "--stop":
            stop = True

    if stop:
        if len(values) > 0:
            help()
            sys.exit(1)
    else:
        if len(values) == 0:
            program = sys.stdin.read()
        elif len(values) == 1:
            with open(values[0]) as f:
                program = f.read()
        else:
            help()
            sys.exit(1)

    status = 0

    with ClientAsync(debug=debug) as client:

        async def prog():
            global status
            with await client.lock() as node_id_str:
                if stop:
                    error = await client.stop(node_id_str)
                    if error is not None:
                        print(f"Stop error {error['error_code']}")
                        status = 2
                else:
                    if scratchpad < 2:
                        error = await client.compile(node_id_str, program)
                        if error is not None:
                            print(f"Compilation error: {error['error_msg']}")
                            status = 2
                        else:
                            error = await client.run(node_id_str)
                            if error is not None:
                                print(f"Run error {error['error_code']}")
                                status = 2
                    if scratchpad > 0:
                        error = await client.set_scratchpad(node_id_str, program)
                        if error is not None:
                            print(f"Scratchpad error {error['error_code']}")
                            status = 2

        client.run_async_program(prog)

    sys.exit(status)
