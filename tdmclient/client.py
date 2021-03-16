# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import TDMZeroconfBrowser, TDMConnection, FlatBuffer, ThymioFB


class Client(ThymioFB):

    def __init__(self, **kwargs):

        super(Client, self).__init__(**kwargs)

        self.tdm_addr = None
        self.tdm_port = None
        self.tdm = None

        def on_change(is_added, addr, port, ws_port):
            if is_added and self.tdm_addr is None:
                if self.debug >= 1:
                    print(f"TDM {addr}:{port} on")
                self.tdm_addr = addr
                self.tdm_port = port
                self.connect()
                self.send_handshake()
            elif not is_added and addr == self.tdm_addr and port == self.tdm_port:
                if self.debug >= 1:
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

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def send_packet(self, b):
        if self.debug >= 2:
            # check decoding
            fb2 = FlatBuffer()
            fb2.parse(b, self.SCHEMA)
            fb2.dump()

        self.tdm.send_packet(b)

    def send_message(self, msg, schema=None):
        encoded_fb = self.create_message(msg, schema)

        self.send_packet(encoded_fb)

    def send_handshake(self):
        if self.debug >= 1:
            print("send handshake")
        self.send_packet(self.create_msg_handshake())

    def send_lock_node(self, node_id_str, **kwargs):
        if self.debug >= 1:
            print(f"send lock node {node_id_str}")
        self.send_packet(self.create_msg_lock_node(node_id_str, **kwargs))

    def send_unlock_node(self, node_id_str, **kwargs):
        if self.debug >= 1:
            print(f"send unlock node {node_id_str}")
        self.send_packet(self.create_msg_unlock_node(node_id_str, **kwargs))

    def send_program(self, node_id_str, program, load=True, **kwargs):
        if self.debug >= 1:
            print(f"send program to {node_id_str}")
        self.send_packet(self.create_msg_program(node_id_str, program, load, **kwargs))

    def set_vm_execution_state(self, node_id_str, state, **kwargs):
        if self.debug >= 1:
            print(f"send set exec state {state} to {node_id_str}")
        self.send_packet(self.create_msg_set_vm_execution_state(node_id_str, state, **kwargs))

    def send_set_scratchpad(self, node_id_str, program, **kwargs):
        if self.debug >= 1:
            print(f"send set scratchpad to {node_id_str}")
        self.send_packet(self.create_msg_scratchpad_update(node_id_str, program, **kwargs))

    def watch_node(self, node_id_str, flags, **kwargs):
        if self.debug >= 1:
            print(f"send watch node flags={flags} to {node_id_str}")
        self.send_packet(self.create_msg_watch_node(node_id_str, flags, **kwargs))

    def send_register_events(self, node_id_str, events, **kwargs):
        if self.debug >= 1:
            print(f"send register {len(events)} events to {node_id_str}")
        self.send_packet(self.create_msg_register_events(node_id_str, events, **kwargs))

    def send_set_variables(self, node_id_str, var_dict, **kwargs):
        if self.debug >= 1:
            print(f"send set variables {', '.join([f'{name}={var_dict[name]}' for name in var_dict])}")
        self.send_packet(self.create_msg_set_variables(node_id_str, var_dict, **kwargs))

    def process_waiting_messages(self):
        at_least_one = False
        if self.tdm:
            while True:
                msg = self.tdm.receive_packet()
                if msg is None:
                    break
                if self.debug >= 3:
                    print("recv", msg)
                self.process_message(msg)
                at_least_one = True
        return at_least_one
