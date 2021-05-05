# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import sys
import os
import getopt
from time import sleep

from tdmclient import ClientAsync


def help():
    print("""Usage: python3 -m tdmclient.tools.list [options]
Run program on robot, from file or stdin

Options:
  --debug n      display diagnostic information (0=none, 1=basic, 2=more, 3=verbose)
  --help         display this help message and exit
  --robotid=I    robot id; default=any
  --robotname=N  robot name; default=any
  --tdmaddr=H    tdm address (default: localhost or from zeroconf)
  --tdmport=P    tdm port (default: from zeroconf)
""")


if __name__ == "__main__":

    debug = 0
    tdm_addr = None
    tdm_port = None
    robot_id = None
    robot_name = None

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "debug=",
                                              "help",
                                              "robotid=",
                                              "robotname=",
                                              "tdmaddr=",
                                              "tdmport=",
                                          ])
    except getopt.error as err:
        print(str(err))
        sys.exit(1)
    for arg, val in arguments:
        if arg == "--help":
            help()
            sys.exit(0)
        elif arg == "--debug":
            debug = int(val)
        elif arg == "--robotid":
            robot_id = val
        elif arg == "--robotname":
            robot_name = val
        elif arg == "--tdmaddr":
            tdm_addr = val
        elif arg == "--tdmport":
            tdm_port = int(val)

    with ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port, debug=debug) as client:

        for _ in range(50):
            client.process_waiting_messages()
            if len(client.nodes) > 0:
                break
            sleep(0.1)

        for node in client.filter_nodes(client.nodes,
                                        node_id=robot_id, node_name=robot_name):
            print(f"id:       {node.id_str}")
            if "group_id_str" in node.props and node.props["group_id_str"] is not None:
                print(f"group id: {node.props['group_id_str']}")
            if "name" in node.props:
                print(f"name:     {node.props['name']}")
            if "status" in node.props:
                status_str = {
                    ClientAsync.NODE_STATUS_UNKNOWN: "unknown",
                    ClientAsync.NODE_STATUS_CONNECTED: "connected",
                    ClientAsync.NODE_STATUS_AVAILABLE: "available",
                    ClientAsync.NODE_STATUS_BUSY: "busy",
                    ClientAsync.NODE_STATUS_READY: "ready",
                    ClientAsync.NODE_STATUS_DISCONNECTED: "disconnected",
                }[node.status]
                print(f"status:   {node.status} ({status_str})")
            if "capabilities" in node.props:
                print(f"cap:      {node.props['capabilities']}")
            if "fw_version" in node.props:
                print(f"firmware: {node.props['fw_version']}")
            print()
