# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ClientAsync, ThymioFB
import sys
import getopt


def help(**kwargs):
    print(f"""Usage: python3 -m tdmclient info [options]
Display robot description sent by tdm

Options:
  --debug=n      display diagnostic info (0=none (default), 1=basic, 2=more, 3=verbose)
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

    display_variables = True
    display_events = True
    display_native_functions = True

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
                                                  "events",
                                                  "scratchpads",
                                                  "shared-event-descr",
                                                  "shared-variables",
                                                  "variables",
                                                  "vm-state",
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

    if len(values) > 0:
        help(file=sys.stderr)
        return 1

    with ClientAsync(zeroconf=zeroconf, zeroconf_all=zeroconf_all,
                     tdm_addr=tdm_addr, tdm_port=tdm_port, tdm_ws=tdm_ws,
                     tdm_transport=tdm_transport,
                     password=password,
                     debug=debug) as client:

        async def prog():
            node = await client.wait_for_node(node_id=robot_id, node_name=robot_name)
            if display_variables:
                v = await node.var_description()
                if len(v) > 0:
                    print("Variables:")
                    for name in v:
                        print(name if v[name] is None else f"{name}[{v[name]}]")
                    print()
            if display_events:
                e = await node.event_description()
                if len(e) > 0:
                    print("Events:")
                    for name in e:
                        print(name)
                    print()
            if display_native_functions:
                f = await node.function_description()
                if len(f) > 0:
                    print("Native functions:")
                    for name in f:
                        print(f"{name}({','.join(['[' + str(s) + ']' for s in f[name]])})")
                    print()

        client.run_async_program(prog)
