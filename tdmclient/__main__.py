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

def help(**kwargs):
    print(f"""Usage: python3 -m tdmclient tool [tooloptions]
Run a tdmclient tool.

Tool:
  ...

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

getattr(tdmclient.tools, values[0]).main(values)
