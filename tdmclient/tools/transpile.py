# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause


import sys
import getopt
from tdmclient.atranspiler import ATranspiler
import tdmclient.module_thymio

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

    modules = {
        "thymio": tdmclient.module_thymio.ModuleThymio()
    }
    transpiler = ATranspiler()
    transpiler.modules = {**transpiler.modules, **modules}
    transpiler.set_source(src)
    transpiler.transpile()
    if show_print:
        if transpiler.print_format_strings is not None:
            print(transpiler.print_format_strings)
    else:
        print(transpiler.get_output())
