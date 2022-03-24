# This file is part of tdmclient.
# Copyright 2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import asyncio
import websockets
import threading
from tdmclient.server import ServerNode, ServerHandler


class ServerWS:

    PORT = 8597

    def __init__(self, port=None):
        self.port = port or ServerWS.PORT
        self.nodes = set()
        self.instances = set()

        async def ws_handler(websocket, path):
            self.instances.add(websocket)
            msg_queue = []
            server_handler = ServerHandler(self.nodes,
                                           lambda data: msg_queue.append(data))
            try:
                async for message in websocket:
                    server_handler.process_message(message)
                    while len(msg_queue) > 0:
                        reply = msg_queue.pop(0)
                        await websocket.send(reply)
            finally:
                print("close")

        self.ws_server = websockets.serve(ws_handler, port=self.port)
        self.loop = asyncio.get_event_loop()

    def run(self):
        self.loop.run_until_complete(self.ws_server)
        self.loop.run_forever()

    def stop(self):
        """Stop websocket server in a thread-safe way"""
        def s():
            for websocket in self.instances:
                websocket.close()
            self.loop.stop()
        self.loop.call_soon_threadsafe(s)

    async def send(self, websocket, msg):
        try:
            await websocket.send(msg)
        except websockets.ConnectionClosed:
            if websocket in self.instances:
                self.instances.remove(websocket)
