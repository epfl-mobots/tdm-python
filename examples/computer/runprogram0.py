#!/usr/bin/env python3

# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from time import sleep
from tdmclient import Client

if __name__ == "__main__":

    with Client(debug=1) as client:

        # state machine state: 0=init, 1=locked, 2=program sent, 3=done
        state = 0

        try:
            while True:
                if client.process_waiting_messages():
                    if len(client.nodes) > 0:
                        node = client.nodes[0]
                        if state == 0:
                            print("node", node.id_str, "state", state, "node satus", node.status)
                            if node.status == 2:
                                # available
                                node.send_lock_node()
                                state = 1
                        elif state == 1:
                            print("node", node.id_str, "state", state, "node satus", node.status)
                            if node.status == 4:
                                # ready
                                node.send_program("leds.top = [0,20,0]\n")
                                state = 2
                        elif state == 2:
                            if node.status == 4:
                                # ready: run
                                node.set_vm_execution_state(1)
                                state = 3
                else:
                    sleep(0.1)
        except KeyboardInterrupt:
            pass
