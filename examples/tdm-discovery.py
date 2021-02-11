#!/usr/bin/env python3
# Yves Piguet, Jan 2021

import sys
import os
from time import sleep

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from tdmclient import TDMZeroconfBrowser

def on_change(is_added, addr, port, ws_port):
    print(f"{'Add' if is_added else 'Remove'} {addr}:{port}{f', ws port: {ws_port}' if ws_port else ''}")

try:
    with TDMZeroconfBrowser(on_change):
        while True:
            sleep(0.1)
except KeyboardInterrupt:
    pass
