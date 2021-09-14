# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Communication with Thymio Device Manager via websocket
Author: Yves Piguet, EPFL
"""

import socket
import io
import threading
import queue
import time
from typing import Awaitable, Callable, List, Optional, Set, Tuple


class TDMConnectionWS:

    DEFAULT_PORT = 8597

    def __init__(self, host=None, port=None)
        self.host = host or "127.0.0.1"
        self.port = port or self.DEFAULT_PORT

    def connect(self):
        self.ws = WebSocket()
