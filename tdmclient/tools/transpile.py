# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause


import sys
import getopt
from tdmclient.atranspiler import ATranspiler

def help():
    print("""Usage: python3 -m tdmclient.tools.transpile [options] [filename]
Run program on robot, from file or stdin

Options:
  --help         display this help message and exit
  --print        display the client-side print statements
""")


if __name__ == "__main__":

    show_print = False

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "help",
                                              "print",
                                          ])
    except getopt.error as err:
        print(str(err))
        sys.exit(1)
    for arg, val in arguments:
        if arg == "--help":
            help()
            sys.exit(0)
        elif arg == "--print":
            show_print = True

    src = None
    if len(values) > 0:
        with open(values[0]) as f:
            src = f.read()
    else:
        src = sys.stdin.read()

    output_src, print_statements, _, _ = ATranspiler.simple_transpile(src)
    if show_print:
        if print_statements is not None:
            print(print_statements)
    else:
        print(output_src)
