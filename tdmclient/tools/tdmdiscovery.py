# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from time import sleep

from tdmclient import TDMZeroconfBrowser

def on_change(is_added, addr, port, ws_port):
    print(f"{'Add' if is_added else 'Remove'} {addr}:{port}{f', ws port: {ws_port}' if ws_port else ''}")

try:
    with TDMZeroconfBrowser(on_change):
        while True:
            sleep(0.1)
except KeyboardInterrupt:
    pass
