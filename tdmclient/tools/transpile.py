# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause


import sys
import getopt
from tdmclient.atranspiler import ATranspiler
import tdmclient.module_thymio
import tdmclient.module_clock
from tdmclient.atranspiler_warnings import missing_global_decl

def help():
    print("""Usage: python3 -m tdmclient transpile [options] [filename]
Run program on robot, from file or stdin

Options:
  --help                    display this help message and exit
  --nothymio                don't import the symbols of thymio library
  --print                   display the client-side print statements
  --warning-missing-global  display warnings for local variables which hide
                            global variables with the same name
""")


def main(argv=None):
    show_print = False
    show_exit = False
    show_events = False
    import_thymio = True
    warning_missing_global = False

    if argv is not None:
        try:
            arguments, values = getopt.getopt(argv[1:],
                                              "",
                                              [
                                                  "events",
                                                  "exit",
                                                  "help",
                                                  "nothymio",
                                                  "print",
                                                  "warning-missing-global",
                                              ])
        except getopt.error as err:
            print(str(err))
            return 1
        for arg, val in arguments:
            if arg == "--events":
                show_events = True
            elif arg == "--exit":
                show_exit = True
            elif arg == "--help":
                help()
                return 0
            elif arg == "--nothymio":
                import_thymio = False
            elif arg == "--print":
                show_print = True
            elif arg == "--warning-missing-global":
                warning_missing_global = True

    src = None
    if len(values) > 0:
        with open(values[0]) as f:
            src = f.read()
    else:
        src = sys.stdin.read()

    transpiler = ATranspiler()
    modules = {
        "thymio": tdmclient.module_thymio.ModuleThymio(transpiler),
        "clock": tdmclient.module_clock.ModuleClock(transpiler),
    }
    transpiler.modules = {**transpiler.modules, **modules}
    if import_thymio:
        transpiler.set_preamble("""from thymio import *
""")
    transpiler.set_source(src)
    transpiler.transpile()

    if warning_missing_global:
        w = missing_global_decl(transpiler)
        for function_name in w:
            for var_name in w[function_name]:
                print(f"Warning: in function '{function_name}', '{var_name}' hides global variable.",
                      file=sys.stderr)
    if show_events:
        if len(transpiler.events_in) + len(transpiler.events_out) > 0:
            print({**transpiler.events_in, **transpiler.events_out})
    if show_exit:
        if transpiler.has_exit_event:
            print("_exit")
    if show_print:
        if transpiler.print_format_strings is not None:
            print(transpiler.print_format_strings)
    if not show_events and not show_exit and not show_print:
        print(transpiler.get_output())
