#!/usr/bin/env python3
# Yves Piguet, Jan-Mar 2021

import sys
import getopt

from tdmclient import ClientAsync

def help():
    print("""Usage: python3 -m tdmclient.tools.run [options] [filename]
Run program on robot, from file or stdin

Options:
  --debug n   display diagnostic information (0=none, 1=basic, 2=more, 3=verbose)
  --help      display this help message
""")

if __name__ == "__main__":

    debug = 0

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "debug=",
                                              "help",
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
            with await client.lock() as node_id_str:
                error = await client.compile(node_id_str, program)
                if error is not None:
                    print(f"Compilation error: {error['error_msg']}")
                    status = 2
                else:
                    error = await client.run(node_id_str)
                    if error is not None:
                        print(f"Error {error['error_code']}")
                        status = 2

        client.run_async_program(prog)

    sys.exit(status)
