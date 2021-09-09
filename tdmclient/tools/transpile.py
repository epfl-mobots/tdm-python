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
  --nothymio     don't import the symbols of thymio library
  --print        display the client-side print statements
""")


if __name__ == "__main__":

    show_print = False
    show_exit = False
    show_events = False
    import_thymio = True

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "events",
                                              "exit",
                                              "help",
                                              "nothymio",
                                              "print",
                                          ])
    except getopt.error as err:
        print(str(err))
        sys.exit(1)
    for arg, val in arguments:
        if arg == "--events":
            show_events = True
        elif arg == "--exit":
            show_exit = True
        elif arg == "--help":
            help()
            sys.exit(0)
        elif arg == "--nothymio":
            import_thymio = False
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
    if import_thymio:
        transpiler.set_preamble("""from thymio import *
""")
    transpiler.set_source(src)
    transpiler.transpile()
    if show_events:
        if len(transpiler.events) > 0:
            print(transpiler.events)
    if show_exit:
        if transpiler.has_exit_event:
            print("_exit")
    if show_print:
        if transpiler.print_format_strings is not None:
            print(transpiler.print_format_strings)
    if not show_events and not show_exit and not show_print:
        print(transpiler.get_output())
