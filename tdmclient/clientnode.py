# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import Node


class ClientNode(Node):

    def __init__(self, thymio, node_dict):

        super(ClientNode, self).__init__(thymio, node_dict)

    def send_request_vm_description(self, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send request vm description {self.id_str}")
        self.thymio.send_packet(self.create_msg_request_vm_description(**kwargs))

    def send_lock_node(self, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send lock node {self.id_str}")
        self.thymio.send_packet(self.create_msg_lock_node(**kwargs))

    def send_unlock_node(self, ignore_disconnected_error=False, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send unlock node {self.id_str}")
        self.thymio.send_packet(self.create_msg_unlock_node(**kwargs),
                                ignore_disconnected_error=ignore_disconnected_error)

    def send_rename_node(self, name, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send rename node {self.id_str} as {name}")
        self.thymio.send_packet(self.create_msg_rename_node(name, **kwargs))

    def send_program(self, program, load=True, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send program to {self.id_str}")
        self.thymio.send_packet(self.create_msg_program(program, load, **kwargs))

    def set_vm_execution_state(self, state, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send set exec state {state} to {self.id_str}")
        self.thymio.send_packet(self.create_msg_set_vm_execution_state(state, **kwargs))

    def send_set_scratchpad(self, program, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send set scratchpad to {self.id_str}")
        self.thymio.send_packet(self.create_msg_scratchpad_update(program, **kwargs))

    def watch_node(self, flags, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send watch node flags={flags} to {self.id_str}")
        self.thymio.send_packet(self.create_msg_watch_node(flags, **kwargs))

    def send_register_events(self, events, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send register {len(events)} events to {self.id_str}")
        self.thymio.send_packet(self.create_msg_register_events(events, **kwargs))

    def send_send_events(self, event_dict, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send events to {self.id_str} {', '.join([f'{name}={event_dict[name]}' for name in event_dict])}")
        self.thymio.send_packet(self.create_msg_send_events(event_dict, **kwargs))

    def send_set_variables(self, var_dict, **kwargs):
        if self.thymio.debug >= 1:
            print(f"send set variables for {self.id_str} {', '.join([f'{name}={var_dict[name]}' for name in var_dict])}")
        self.thymio.send_packet(self.create_msg_set_variables(var_dict, **kwargs))
