# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Tool entry point.
"""

import tdmclient.tools
import sys
import getopt

tool_set = {
    "gui",
    "list",
    "repl",
    "run",
    "server",
    "tdmdiscovery",
    "transpile",
    "watch",
}

def help(**kwargs):
    print(f"""Usage: python3 -m tdmclient tool [tooloptions]
Run a tdmclient tool.

Tool:
  {", ".join(sorted(tool_set))}

For help about tool-specific options, type

  python3 -m tdmclient tool --help
""", **kwargs)


try:
    arguments, values = getopt.getopt(sys.argv[1:],
                                      "",
                                      [
                                          "help",
                                      ])
except getopt.error as err:
    print(str(err))
    sys.exit(1)

for arg, val in arguments:
    if arg == "--help":
        help()
        sys.exit(0)

if len(values) == 0:
    help(file=sys.stderr)
    sys.exit(1)

tool_name = values[0]
if tool_name not in tool_set:
    print(f"Unknown tool {tool_name}.\n", file=sys.stderr)
    help(file=sys.stderr)
    sys.exit(1)

sys.exit(getattr(tdmclient.tools, tool_name).main(values))
