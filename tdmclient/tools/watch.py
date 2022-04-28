# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ClientAsync
import sys
import getopt


def help(**kwargs):
    print(f"""Usage: python3 -m tdmclient watch [options]
Watch information on robot sent by tdm

Options:
  --debug=n      display diagnostic info (0=none, 1=basic, 2=more (default), 3=verbose)
  --help         display this help message and exit
  --password=PWD specify password for remote tdm
  --robotid=I    robot id; default=any
  --robotname=N  robot name; default=any
  --tdmaddr=H    tdm address (default: localhost or from zeroconf)
  --tdmport=P    tdm port or "default" for {ClientAsync.DEFAULT_TDM_PORT} (default: from zeroconf)
  --tdmws        connect to tdm with WebSocket (default: plain TCP)
""", **kwargs)


def main(argv=None, tdm_transport=None):
    debug = 2  # display all messages received from the tdm by default
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

    if len(values) > 0:
        help(file=sys.stderr)
        return 1

    with ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port, tdm_ws=tdm_ws,
                     tdm_transport=tdm_transport,
                     password=password,
                     debug=debug) as client:

        async def prog():
            node = await client.wait_for_node(node_id=robot_id, node_name=robot_name)
            await node.watch(flags=0x3f)  # all
            await client.sleep()

        client.run_async_program(prog)
