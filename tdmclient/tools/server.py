# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import Server, ServerNode, ThymioFB
from tdmclient.serverws import ServerWS
import sys
import getopt


def help():
    print(f"""Usage: python3 -m tdmclient.tools.server [options]
Run a dummy tdm server

Options:
  --help         display this help message and exit
  --port=P       port (default: {Server.PORT} for TCP, {ServerWS.PORT} for WebSocket)
  --ws           WebSocket instead of plain TCP
""")


if __name__ == "__main__":

    tdm_port = None
    ws = False

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "help",
                                              "port=",
                                              "ws",
                                          ])
    except getopt.error as err:
        print(str(err))
        sys.exit(1)
    for arg, val in arguments:
        if arg == "--help":
            help()
            sys.exit(0)
        elif arg == "--port":
            tdm_port = int(val)
        elif arg == "--ws":
            ws = True

    node = ServerNode(type=ThymioFB.NODE_TYPE_THYMIO2,
                      variables={
                          "a": [123],
                          "b": [4, 5, 6],
                      })

    if ws:
        server = ServerWS(port=tdm_port)
        server.nodes.add(node)
        server.run()
    else:
        server = Server(port=tdm_port)
        server.nodes.add(node)
        server.start()
        while True:
            server.accept()
