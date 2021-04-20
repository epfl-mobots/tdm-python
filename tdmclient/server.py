# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import socket
import threading
from tdmclient import ThymioFB, FlatBuffer, Union

class ServerThread(threading.Thread):

    def __init__(self, socket, address_client):
        threading.Thread.__init__(self)
        self.socket = socket
        self.address_client = address_client
        self.fb = ThymioFB()

    def read_uint32(self) -> int:
        """Read an unsigned 32-bit number.
        """
        b = self.socket.recv(4)
        if len(b) < 4:
            raise TimeoutError()
        else:
            return b[0] + 256 * (b[1] + 256 * (b[2] + 256 * b[3]))

    def read_packet(self):
        """Read a complete packet.
        """
        packet_len = self.read_uint32()
        packet = self.socket.recv(packet_len)
        return packet

    def run(self) -> None:
        while True:
            try:
                msg = self.read_packet()
                fb = FlatBuffer()
                fb.parse(msg, ThymioFB.SCHEMA)
                print("packet received", fb)
                if type(fb.root) is Union:
                    print(f"Union type={fb.root.union_type}")
            except TimeoutError:
                pass


class Server:

    PORT = 10000

    def __init__(self, port=None):
        self.port = port or Server.PORT
        self.socket_listener = None

    def start(self):
        self.stop()
        self.socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_listener.bind(('', self.port))
        self.socket_listener.listen(5)

    def accept(self):
        socket_client, address = self.socket_listener.accept()
        thr = ServerThread(socket_client, address)
        thr.run()

    def stop(self):
        if self.socket_listener is not None:
            self.socket_listener.close()
