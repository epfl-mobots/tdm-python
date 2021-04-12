# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Communication with Thymio Device Manager via tcp
Author: Yves Piguet, EPFL
"""

import socket
import io
import threading
import queue
import time
from typing import Awaitable, Callable, List, Optional, Set, Tuple


class InputThread(threading.Thread):
    """Thread which reads packets asynchronously.
    """

    def __init__(self, io, io_lock, packet_queue=None):
        threading.Thread.__init__(self)
        self.running = True
        self.io = io
        self.io_lock = io_lock
        self.packet_queue = packet_queue
        self.comm_error = None

    def terminate(self, on_terminated=None) -> None:
        self.on_terminated = on_terminated
        self.running = False

    def read_uint32(self) -> int:
        """Read an unsigned 32-bit number.
        """
        b = self.io.read(4)
        if len(b) < 4:
            raise TimeoutError()
        else:
            return b[0] + 256 * (b[1] + 256 * (b[2] + 256 * b[3]))

    def read_packet(self):
        """Read a complete packet.
        """
        try:
            with self.io_lock:
                if not self.running:
                    raise Exception("closing")
                packet_len = self.read_uint32()
                packet = self.io.read(packet_len)
            return packet
        except Exception as error:
            self.comm_error = error
            raise error

    def run(self) -> None:
        """Input thread code.
        """
        while self.running:
            try:
                packet = self.read_packet()
                if self.packet_queue is not None:
                    self.packet_queue.put(packet)
            except TimeoutError:
                pass
        if self.on_terminated:
            self.on_terminated()


class TDMConnection:
    """Connection to TDM.
    """

    class TDMConnectionError(OSError):
        pass

    def __init__(self,
                 host: str, port: int,
                 debug=False):

        class TCPClientIO(io.RawIOBase):

            def __init__(self, host, port):
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((host, port))

            def read(self, n):
                return self.socket.recv(n)

            def write(self, b):
                self.socket.sendall(b)

        self.io = TCPClientIO(host, port)
        self.debug = debug
        self.timeout = 3
        self.comm_error = None
        self.input_queue = queue.Queue()

        self.io_lock = threading.Lock()
        self.input_lock = threading.Lock()
        self.input_thread = InputThread(self.io,
                                        self.io_lock,
                                        packet_queue=self.input_queue)
        self.input_thread.start()

        self.output_lock = threading.Lock()
        self.shutting_down = False
        self.tasks = set()
        self.refreshing_data_coverage = None    # or set of variables to fetch
        self.refreshing_data_span = None   # or (offset, length) (based on refreshing_data_coverage)
        self.refreshing_triggers = []   # threading.Event

        # callback for communication error notification
        # fun(error)
        self.on_comm_error = None

    def close(self) -> None:
        """Close connection.
        """
        if not self.io.closed:
            # close protected by io_lock to prevent reading more messages
            with self.io_lock:
                if self.debug:
                    print("# close")
                self.io.close()

    def request_shutdown(self, on_terminated=None) -> None:
        """Request a gentle shutdown of the input thread which will be followed
        by closing the connection and calling on_terminated (if not None).
        """
        if self.shutting_down:
            # once is enough
            if on_terminated is not None:
                on_terminated()
            return

        self.shutting_down = True

        def on_terminated1():
            self.close()
            if on_terminated is not None:
                on_terminated()

        self.input_thread.terminate(on_terminated1)

    def __enter__(self) -> None:
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.request_shutdown()

    def send_packet(self, packet) -> None:
        """Send a packet.
        """
        with self.output_lock:
            if self.debug:
                print(">", packet)
            try:
                n = len(packet)
                blen = bytes([(n >> 8 * i) & 0xff for i in range(4)])
                self.io.write(blen + packet)
            except Exception as error:
                self.comm_error = error
                if self.on_comm_error is not None:
                    self.on_comm_error("write: " + str(error))
                raise error

    def receive_packet(self):
        """Get next received packet, or None if none.
        """
        try:
            return self.input_queue.get_nowait()
        except queue.Empty:
            return None
