# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import sys
import getopt
from time import sleep

from tdmclient import TDMZeroconfBrowser

def help(**kwargs):
    print(f"""Usage: python3 -m tdmclient tdmdiscovery [options]
Discover TDM information provided by zeroconf.

Options:
  --help         display this help message and exit
""", **kwargs)

def on_change(is_added, addr, port, ws_port):
    print(f"{'Add' if is_added else 'Remove'} {addr}:{port}{f', ws port: {ws_port}' if ws_port else ''}")

def main(argv=None):
    if argv is not None:
        try:
            arguments, values = getopt.getopt(argv[1:],
                                              "",
                                              [
                                                  "help",
                                              ])
        except getopt.error as err:
            print(str(err))
            return 1
        for arg, val in arguments:
            if arg == "--help":
                help()
                return 0

    try:
        with TDMZeroconfBrowser(on_change):
            while True:
                sleep(0.1)
    except KeyboardInterrupt:
        pass
