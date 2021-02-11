#!/usr/bin/env python3
# Yves Piguet, Jan-Feb 2021

import sys
import os
from time import sleep

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from tdmclient import TDMZeroconfBrowser, TDMConnection, FlatBuffer, Union, Table, ThymioFB


class Test(ThymioFB):

    def __init__(self, **kwargs):

        super(Test, self).__init__(**kwargs)

        self.tdm_addr = None
        self.tdm_port = None
        self.tdm = None

        def on_change(is_added, addr, port, ws_port):
            if is_added and self.tdm_addr is None:
                if self.debug:
                    print(f"TDM {addr}:{port} on")
                self.tdm_addr = addr
                self.tdm_port = port
                self.connect()
                self.send_handshake()
            elif not is_added and addr == self.tdm_addr and port == self.tdm_port:
                if self.debug:
                    print(f"TDM {addr}:{port} off")
                self.disconnect()
                self.tdm_addr = None
                self.tdm_port = None

        self.zc = TDMZeroconfBrowser(on_change)

    def close(self):
        self.zc.close()

    def connect(self):
        self.tdm = TDMConnection(self.tdm_addr, self.tdm_port)

    def disconnect(self):
        if self.tdm is not None:
            self.tdm.close()
            self.tdm = None

    def send_packet(self, b):
        self.tdm.send_packet(b)

    def send_message(self, msg, schema=None):
        encoded_fb = self.create_message(msg, schema)

        if self.debug:
            # check decoding
            fb2 = FlatBuffer()
            fb2.parse(encoded_fb, self.SCHEMA)
            fb2.dump()

        self.send_packet(encoded_fb)

    def send_handshake(self):
        if self.debug:
            print("send handshake")
        self.send_packet(self.create_msg_handshake())

    def send_lock_node(self, node_id_str):
        if self.debug:
            print(f"send lock node {node_id_str}")
        self.send_packet(self.create_msg_lock_node(node_id_str))

    def send_unlock_node(self, node_id_str):
        if self.debug:
            print(f"send unlock node {node_id_str}")
        self.send_packet(self.create_msg_unlock_node(node_id_str))

    def send_program(self, node_id_str, program, load=True):
        if self.debug:
            print(f"send program to {node_id_str}")
        self.send_packet(self.create_msg_program(node_id_str, program, load))

    def set_vm_execution_state(self, node_id_str, state):
        if self.debug:
            print(f"send set exec state {state} to {node_id_str}")
        self.send_packet(self.create_msg_set_vm_execution_state(node_id_str, state))

    def process_next_message(self):
        if self.tdm:
            msg = self.tdm.receive_packet()
            if msg is not None:
                if self.debug:
                    print("recv", msg)
                self.process_message(msg)


test = Test(debug=False)

# state machine state: 0=init, 1=locked, 2=program sent, 3=done
state = 0

try:
    while True:
        test.process_next_message()
        sleep(0.1)
        if len(test.nodes) > 0:
            node = test.nodes[0]
            node_id_str = node["node_id_str"]
            status = node["status"]
            if state == 0:
                print("node", node_id_str, "state", state, "node satus", status)
                if status == 2:
                    # available
                    test.send_lock_node(node_id_str)
                    state = 1
            elif state == 1:
                print("node", node_id_str, "state", state, "node satus", status)
                if status == 4:
                    # ready
                    test.send_program(node_id_str,
                                      "leds.top = [0,0,32]\n")
                    state = 2
            elif state == 2:
                if status == 4:
                    # ready: run
                    test.set_vm_execution_state(node_id_str, 1)
                    state = 3
except KeyboardInterrupt:
    pass

test.close()
