# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Communication with TDM.
"""

from tdmclient.fb import FlatBuffer, Table, Union
from tdmclient.zeroconf import TDMZeroconfBrowser
from tdmclient.tcp import TDMConnection
try:
    from tdmclient.ws import TDMConnectionWS
except ModuleNotFoundError:
    pass
from tdmclient.thymio import ThymioFB, Node
from tdmclient.client import Client
from tdmclient.clientasync import ClientAsync, NodeLockError
from tdmclient.clientnode import ClientNode
from tdmclient.clientasyncnode import ClientAsyncNode
from tdmclient.clientasynccachenode import ClientAsyncCacheNode, ArrayCache
from tdmclient.repl import TDMConsole

from tdmclient.server import (Server, ServerNode,
                              ServerRawTDMHandler, ServerHandler)

# shortcut
aw = ClientAsync.aw
