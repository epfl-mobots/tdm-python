# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Communication with Thymio Device Manager via websocket
Author: Yves Piguet, EPFL
"""

from . import TDMConnection
import websocket
import socket


class TDMConnectionWS(TDMConnection):
    """Connection to TDM via WebSocket.
    """

    DEFAULT_PORT = 8597

    # timeout for non-blocking recv; default timeout for everything else
    SMALL_TIMEOUT = 0.001

    def __init__(self,
                 host=None, port=None,
                 debug=False):
        self.host = host or "127.0.0.1"
        self.port = port or self.DEFAULT_PORT
        self.debug = debug

        url = f"ws://{self.host}:{self.port}/"
        self.ws = websocket.WebSocket()
        self.ws.connect(url)

    def close(self) -> None:
        """Close connection.
        """
        if self.ws is not None:
            self.ws.close()
            self.ws = None

    def request_shutdown(self, on_terminated=None):
        self.close()
        if on_terminated is not None:
            on_terminated()

    def send_packet(self, packet) -> None:
        """Send a packet.
        """
        if self.debug:
            print(">", packet)
        self.ws.send_binary(packet)

    def receive_packet(self):
        """Get next received packet, or None if none.
        """
        timeout_orig = self.ws.gettimeout()
        self.ws.sock.settimeout(self.SMALL_TIMEOUT)
        try:
            return self.ws.recv()
        except websocket.WebSocketTimeoutException:
            return None
        finally:
            self.ws.sock.settimeout(timeout_orig)
