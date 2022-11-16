# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import sys
import getopt
from time import sleep

from tdmclient import ClientAsync


def help():
    print(f"""Usage: python3 -m tdmclient list [options]
Run program on robot, from file or stdin

Options:
  --debug n      display diagnostic information (0=none, 1=basic, 2=more, 3=verbose)
  --help         display this help message and exit
  --password=PWD specify password for remote tdm
  --robotid=I    robot id; default=any
  --robotname=N  robot name; default=any
  --tdmaddr=H    tdm address (default: localhost or from zeroconf)
  --tdmport=P    tdm port (default: 8596 (tcp) or 8597 (ws), or from zeroconf)
  --tdmws        connect to tdm with WebSocket (default: plain TCP)
  --zeroconf     use zeroconf (default: no zeroconf)
  --zcall        discover TDM information published on all interfaces instead
                 of only default one
""")


def get_product_id(node):
    """Get as a 2-element tuple the product id (value of variable "_productId")
    as a number and its meaning as a string, or None if not available or unknown
    """
    product_id = None
    ClientAsync.aw(node.wait_for_variables())
    if "_productId" in node:
        product_id = node["_productId"]
        d = {
            0: "undefined",
            1: "aseba challenge",
            2: "playground e-puck",
            3: "marxbot",
            4: "handbot",
            5: "e-puck",
            6: "Smartrob",
            7: "Smartrob ASL",
            8: "Thymio II",
        }
        return product_id, d[product_id] if product_id in d else None
    else:
        return None, None


def main(argv=None, tdm_transport=None):
    debug = 0
    zeroconf = False
    zeroconf_all = False
    tdm_addr = None
    tdm_port = None
    tdm_ws = False
    password = None
    robot_id = None
    robot_name = None

    if argv is not None:
        try:
            arguments, values = getopt.getopt(argv[1:],
                                              "",
                                              [
                                                  "debug=",
                                                  "help",
                                                  "password=",
                                                  "robotid=",
                                                  "robotname=",
                                                  "tdmaddr=",
                                                  "tdmport=",
                                                  "tdmws",
                                                  "zeroconf",
                                                  "zcall",
                                              ])
        except getopt.error as err:
            print(str(err))
            return 1
        for arg, val in arguments:
            if arg == "--help":
                help()
                return 0
            elif arg == "--debug":
                debug = int(val)
            elif arg == "--password":
                password = val
            elif arg == "--robotid":
                robot_id = val
            elif arg == "--robotname":
                robot_name = val
            elif arg == "--tdmaddr":
                tdm_addr = val
            elif arg == "--tdmport":
                tdm_port = ClientAsync.DEFAULT_TDM_PORT if val == "default" else int(val)
            elif arg == "--tdmws":
                tdm_ws = True
            elif arg == "--zeroconf":
                zeroconf = True
            elif arg == "--zcall":
                zeroconf = True
                zeroconf_all = True

    with ClientAsync(zeroconf=zeroconf, zeroconf_all=zeroconf_all,
                     tdm_addr=tdm_addr, tdm_port=tdm_port, tdm_ws=tdm_ws,
                     tdm_transport=tdm_transport,
                     password=password,
                     debug=debug) as client:

        for _ in range(50):
            client.process_waiting_messages()
            if len(client.nodes) > 0:
                break
            sleep(0.1)

        for node in client.filter_nodes(client.nodes,
                                        node_id=robot_id, node_name=robot_name):
            print(f"id:         {node.id_str}")
            if "group_id_str" in node.props and node.props["group_id_str"] is not None:
                print(f"group id:   {node.props['group_id_str']}")
            if "type" in node.props:
                try:
                    type_str = {
                        ClientAsync.NODE_TYPE_THYMIO2: "Thymio II",
                        ClientAsync.NODE_TYPE_THYMIO2WIRELESS: "Thymio II wireless",
                        ClientAsync.NODE_TYPE_SIMULATED_THYMIO2: "Simulated Thymio II",
                        ClientAsync.NODE_TYPE_DUMMY_NODE: "Dummy node",
                        ClientAsync.NODE_TYPE_UNKNOWN_TYPE: "Unknown type",
                    }[node.props["type"]]
                    print(f"type:       {node.props['type']} ({type_str})")
                except KeyError:
                    pass
            product_id, product_name = get_product_id(node)
            if product_name is not None:
                print(f"product id: {product_id} ({product_name})")
            else:
                print(f"product id: {product_id}")
            if "name" in node.props:
                print(f"name:       {node.props['name']}")
            if "status" in node.props:
                status_str = {
                    ClientAsync.NODE_STATUS_UNKNOWN: "unknown",
                    ClientAsync.NODE_STATUS_CONNECTED: "connected",
                    ClientAsync.NODE_STATUS_AVAILABLE: "available",
                    ClientAsync.NODE_STATUS_BUSY: "busy",
                    ClientAsync.NODE_STATUS_READY: "ready",
                    ClientAsync.NODE_STATUS_DISCONNECTED: "disconnected",
                }[node.status]
                print(f"status:     {node.status} ({status_str})")
            if "capabilities" in node.props:
                print(f"cap:        {node.props['capabilities']}")
            if "fw_version" in node.props:
                print(f"firmware:   {node.props['fw_version']}")
            print()
