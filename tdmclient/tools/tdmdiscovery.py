#!/usr/bin/env python3
# Yves Piguet, Jan 2021

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
