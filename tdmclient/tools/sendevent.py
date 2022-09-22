# This file is part of tdmclient.
# Copyright 2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ClientAsync, ThymioFB
import sys
import getopt


def help(**kwargs):
    print(f"""Usage: python3 -m tdmclient sendevent [options]
Send event to robot

Options:
  --data=val     event data, as an int or array of int (default: empty)
  --debug=n      display diagnostic info
                 (0=none, 1=basic, 2=more (default), 3=verbose)
  --event=name   event name (required)
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
""", **kwargs)


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
    event_name = None
    event_data = None
    lock_node = True  # current tdm restriction

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
                                                  "zcall",
                                                  "zeroconf",
                                                  "event=",
                                                  "data=",
                                              ])
        except getopt.error as err:
            print(str(err), file=sys.stderr)
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
            elif arg == "--event":
                event_name = val
            elif arg == "--data":
                if val[0] == "[" and val[-1] == "]":
                    event_data = [
                        int(s)
                        for s in val[1:-1].split(",")
                    ]
                else:
                    event_data = [int(val)]

    if len(values) > 0:
        help(file=sys.stderr)
        return 1

    if event_name is None:
        print("Missing --event option", file=sys.stderr)
        sys.exit(1)
        flags = ThymioFB.WATCHABLE_INFO_ALL

    event_dict = {
        event_name: event_data if event_data is not None else [],
    }

    with ClientAsync(zeroconf=zeroconf, zeroconf_all=zeroconf_all,
                     tdm_addr=tdm_addr, tdm_port=tdm_port, tdm_ws=tdm_ws,
                     tdm_transport=tdm_transport,
                     password=password,
                     debug=debug) as client:

        if lock_node:
            async def prog():
                with await client.lock(node_id=robot_id, node_name=robot_name) as node:
                    await node.send_events(event_dict)
        else:
            async def prog():
                node = await client.wait_for_node(node_id=robot_id, node_name=robot_name)
                await node.send_events(event_dict)

        client.run_async_program(prog)
