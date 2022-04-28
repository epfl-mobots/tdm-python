# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import Server, ServerNode, ThymioFB
from tdmclient.serverws import ServerWS
import sys
import getopt


def help():
    print(f"""Usage: python3 -m tdmclient server [options]
Run a dummy tdm server

Options:
  --debug        display debugging information
  --help         display this help message and exit
  --port=P       port (default: {Server.PORT} for TCP, {ServerWS.PORT} for WebSocket)
  --ws           WebSocket in addition to plain TCP
  --zeroconf     advertise TCP TDM port via zeroconf
""")


def main(argv=None):
    tdm_port = None
    ws = False
    adv_zeroconf = False
    debug = False

    if argv is not None:
        try:
            arguments, values = getopt.getopt(argv[1:],
                                              "",
                                              [
                                                  "debug",
                                                  "help",
                                                  "port=",
                                                  "ws",
                                                  "zeroconf",
                                              ])
        except getopt.error as err:
            print(str(err))
            return 1
        for arg, val in arguments:
            if arg == "--debug":
                debug = True
            elif arg == "--help":
                help()
                return 0
            elif arg == "--port":
                tdm_port = int(val)
            elif arg == "--ws":
                ws = True
            elif arg == "--zeroconf":
                adv_zeroconf = True

    if adv_zeroconf:
        from zeroconf import Zeroconf, ServiceInfo
        import socket
        import uuid

        service_props = {
            "uuid": str(uuid.uuid4())
        }
        if ws:
            service_props["ws-port"] = str(tdm_port or ServerWS.PORT)

        info = ServiceInfo(
            "_mobsya._tcp.local.",
            "Python tdmclient_tools_server._mobsya._tcp.local.",
            weight=100,
            addresses=[socket.inet_aton("127.0.0.1")],
            port=tdm_port or Server.PORT,
            properties=service_props,
        )

        zeroconf = Zeroconf()
        zeroconf.register_service(info)

    node = ServerNode(type=ThymioFB.NODE_TYPE_THYMIO2,
                      variables={
                          "a": [123],
                          "b": [4, 5, 6],
                      })

    # prepare TCP server
    server = Server(port=tdm_port, debug=debug)
    server.nodes.add(node)
    server.start()

    if ws:
        # run both TCP and WebSocket servers
        server.start_main_thread()
        server_ws = ServerWS(port=tdm_port, debug=debug)
        server_ws.nodes.add(node)
        server_ws.run()
    else:
        # only TCP server: don't need a separate thread
        server.loop_forever()
