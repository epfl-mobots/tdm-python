# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

# publish service with zeroconf (Linux or Windows):
# dns-sd -R "Thymio Device Manager" _mobsya._tcp local 10000 ws-port=8999 uuid='ce0120f3-b46d-49ad-aba1-dafca3466d99'

import socket
import threading
import uuid
from tdmclient import ThymioFB, FlatBuffer, Union


class ServerNode:

    robot_count = 0

    def __init__(self,
                 id=None,
                 type=ThymioFB.NODE_TYPE_DUMMY_NODE,
                 name=None,
                 variables=None):
        self.id = id or str(uuid.uuid4())
        if name is None:
            self.robot_count += 1
            self.name = f"Robot {self.robot_count}"
        else:
            self.name = name
        self.status = ThymioFB.NODE_STATUS_AVAILABLE
        self.type = type
        self.capabilities = ThymioFB.NODE_CAPABILITY_RENAME
        self.bytecode_size = 1600
        self.data_size = 600
        self.stack_size = 100
        self.variables = variables or {}
        self.events = {}
        self.execution_state = ThymioFB.VM_EXECUTION_STATE_STOPPED

    def __repr__(self):
        return f"Node {self.id}"


class ServerThread(threading.Thread):

    def __init__(self, server, socket, address_client):
        threading.Thread.__init__(self)
        self.server = server
        self.socket = socket
        self.address_client = address_client
        self.thymio = ThymioFB()

    def read_uint32(self) -> int:
        """Read an unsigned 32-bit number.
        """
        b = self.socket.recv(4)
        if len(b) < 4:
            raise TimeoutError()
        else:
            return b[0] + 256 * (b[1] + 256 * (b[2] + 256 * b[3]))

    def read_packet(self):
        """Read a complete packet.
        """
        packet_len = self.read_uint32()
        packet = self.socket.recv(packet_len)
        return packet

    def send_packet(self, packet) -> None:
        """Send a packet.
        """
        n = len(packet)
        blen = bytes([(n >> 8 * i) & 0xff for i in range(4)])
        self.socket.sendall(blen + packet)

    def send_nodes_changed(self):
        msg = self.thymio.create_message((
            ThymioFB.MESSAGE_TYPE_NODES_CHANGED,
            (
                [
                    (
                        (
                            ThymioFB.id_str_to_bytes(node.id),
                        ),
                        # group id
                        (
                            ThymioFB.id_str_to_bytes(node.id),
                        ),
                        node.status,
                        node.type,
                        node.name,
                        node.capabilities,
                        "14",
                        "14",
                    )
                    for node in self.server.nodes
                ],
            ),
        ), ThymioFB.SCHEMA)
        self.send_packet(msg)
        print(f"-> {len(self.server.nodes)} node(s) changed")
        for node in self.server.nodes:
            print(f"   {node.id}: status={node.status}, type={node.type}, name={node.name}, cap={node.capabilities}")

    def send_variables_changed(self, node):
        msg = self.thymio.create_message((
            ThymioFB.MESSAGE_TYPE_VARIABLES_CHANGED,
            (
                (
                    ThymioFB.id_str_to_bytes(node.id),
                ),
                [
                    (
                        name,
                        node.variables[name],
                    )
                    for name in node.variables
                ],
                # timestamp: left unspecified
            ),
        ), ThymioFB.SCHEMA)
        self.send_packet(msg)
        print(f"-> var of {node.id} changed")

    def run(self) -> None:

        while True:
            try:
                msg = self.read_packet()
                fb = FlatBuffer()
                fb.parse(msg, ThymioFB.SCHEMA)
                if type(fb.root) is Union:
                    print(f"<- type={fb.root.union_type}")
                    if fb.root.union_type == ThymioFB.MESSAGE_TYPE_CONNECTION_HANDSHAKE:
                        # send back handshake
                        msg = self.thymio.create_message((
                            ThymioFB.MESSAGE_TYPE_CONNECTION_HANDSHAKE,
                            ()
                        ), ThymioFB.SCHEMA)
                        self.send_packet(msg)
                        # send node changed for all nodes
                        self.send_nodes_changed()
                        # send variables changed for all nodes
                        for node in self.server.nodes:
                            self.send_variables_changed(node)
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_REQUEST_NODE_ASEBA_VM_DESCRIPTION:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        node = self.server.findNode(node_id_str)
                        if node is not None:
                            msg = self.thymio.create_message((
#T(iT(*u)iii*T(2si)*T(2ss)*T(2ss*T(si)))
                                ThymioFB.MESSAGE_TYPE_NODE_ASEBA_VM_DESCRIPTION,
                                (
                                    request_id,
                                    (
                                        ThymioFB.id_str_to_bytes(node.id),
                                    ),
                                    node.bytecode_size,
                                    node.data_size,
                                    node.stack_size,
                                    [
                                        (
                                            len(node.variables[name]),
                                            name,
                                        )
                                        for name in node.variables
                                    ],
                                    [],
                                    [],
                                )
                            ), ThymioFB.SCHEMA)
                            print(f"-> {node.id} locked")
                        else:
                            msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN_NODE)
                            print(f"-> unknown {node.id}")
                        self.send_packet(msg)
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_LOCK_NODE:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        node = self.server.findNode(node_id_str)
                        if node is not None:
                            if node.status == ThymioFB.NODE_STATUS_AVAILABLE:
                                node.status = ThymioFB.NODE_STATUS_READY
                                msg = self.thymio.create_msg_request_completed(request_id)
                                print(f"-> {node.id} locked")
                                self.send_nodes_changed()
                            else:
                                msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_NODE_BUSY)
                                print(f"-> lock error: {node.id} busy")
                        else:
                            msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN_NODE)
                            print(f"-> unknown {node.id}")
                        self.send_packet(msg)
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_UNLOCK_NODE:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        node = self.server.findNode(node_id_str)
                        if node is not None:
                            if node.status == ThymioFB.NODE_STATUS_READY:
                                node.status = ThymioFB.NODE_STATUS_AVAILABLE
                                msg = self.thymio.create_msg_request_completed(request_id)
                                self.send_packet(msg)
                                print(f"-> {node.id} unlocked")
                                self.send_nodes_changed()
                            else:
                                msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN)
                                self.send_packet(msg)
                                print(f"-> unlock error: {node.id} not locked")
                        else:
                            msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN_NODE)
                            self.send_packet(msg)
                            print(f"-> unknown node {node.id}")
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_COMPILE_AND_LOAD_CODE_ON_VM:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        node = self.server.findNode(node_id_str)
                        if node is not None:
                            language = FlatBuffer.field_val(fb.root.union_data[0].fields[2], ThymioFB.PROGRAMMING_LANGUAGE_ASEBA)
                            program = FlatBuffer.field_val(fb.root.union_data[0].fields[3], "")
                            options = FlatBuffer.field_val(fb.root.union_data[0].fields[4], 0)
                            print(f"Source code:\n{program}")
                            msg = self.thymio.create_msg_compilation_result_success(request_id,
                                                                                    0, node.bytecode_size,
                                                                                    0, node.data_size)
                            self.send_packet(msg)
                            print(f"-> compilation ok")
                        else:
                            msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN_NODE)
                            self.send_packet(msg)
                            print(f"-> unknown node {node.id}")
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_WATCH_NODE:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        flags = FlatBuffer.field_val(fb.root.union_data[0].fields[2], 0)
                        node = self.server.findNode(node_id_str)
                        if node is not None:
                            node.watch_flags = flags
                            print(f"Node {node_id_str}: watch flags := 0x{flags:x}")
                            msg = self.thymio.create_msg_request_completed(request_id)
                            self.send_packet(msg)
                        else:
                            msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN_NODE)
                            self.send_packet(msg)
                            print(f"-> unknown node {node_id_str}")
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_SET_VARIABLES:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        variables = {
                            v.fields[0][0]: v.fields[1][0]
                            for v in fb.root.union_data[0].fields[2][0]
                        }
                        node = self.server.findNode(node_id_str)
                        if node is not None:
                            node.variables = {**node.variables, **variables}
                            msg = self.thymio.create_msg_request_completed(request_id)
                            self.send_packet(msg)
                            self.send_variables_changed(node)
                        else:
                            msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN_NODE)
                            self.send_packet(msg)
                            print(f"-> unknown node {node.id}")
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_REGISTER_EVENTS:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        events = {
                            e.fields[0][0]: e.fields[1][0]
                            for e in fb.root.union_data[0].fields[2][0]
                        }
                        node = self.server.findNode(node_id_str)
                        if node is not None:
                            node.events = events
                            msg = self.thymio.create_msg_request_completed(request_id)
                            self.send_packet(msg)
                        else:
                            msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN_NODE)
                            self.send_packet(msg)
                            print(f"-> unknown node {node.id}")
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_SET_BREAKPOINTS:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        breakpoints = [
                            bp.fields[0][0]
                            for bp in fb.root.union_data[0].fields[2][0]
                        ]
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_SET_VM_EXECUTION_STATE:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        node = self.server.findNode(node_id_str)
                        if node is not None:
                            command = FlatBuffer.field_val(fb.root.union_data[0].fields[2], ThymioFB.VM_EXECUTION_STATE_COMMAND_STOP)
                            if command == ThymioFB.VM_EXECUTION_STATE_COMMAND_STOP:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_STOPPED
                            elif command == ThymioFB.VM_EXECUTION_STATE_COMMAND_RUN:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_RUNNING
                            elif command == ThymioFB.VM_EXECUTION_STATE_COMMAND_STEP:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_PAUSED
                            elif command == ThymioFB.VM_EXECUTION_STATE_COMMAND_STEP_TO_NEXT_LINE:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_PAUSED
                            elif command == ThymioFB.VM_EXECUTION_STATE_COMMAND_PAUSE:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_PAUSED
                            elif command == ThymioFB.VM_EXECUTION_STATE_COMMAND_RESET:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_RUNNING
                            elif command == ThymioFB.VM_EXECUTION_STATE_COMMAND_REBOOT:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_STOPPED
                            elif command == ThymioFB.VM_EXECUTION_STATE_COMMAND_SUSPEND:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_PAUSED
                            elif command == ThymioFB.VM_EXECUTION_STATE_COMMAND_WRITE_PROGRAM_TO_DEVICE_MEMORY:
                                node.execution_state = ThymioFB.VM_EXECUTION_STATE_STOPPED
                            msg = self.thymio.create_msg_request_completed(request_id)
                            self.send_packet(msg)
                            print(f"-> ok")
                            msg = self.thymio.create_msg_request_completed(request_id)
                            self.send_packet(msg)
                            print(f"-> ok")
                            msg = self.thymio.create_msg_vm_execution_state_changed(node_id_str, node.execution_state, 1, ThymioFB.ERROR_NO_ERROR, "")
                            self.send_packet(msg)
                            print(f"-> state = {node.execution_state}")
                        else:
                            msg = self.thymio.create_msg_error(request_id, ThymioFB.ERROR_UNKNOWN_NODE)
                            self.send_packet(msg)
                            print(f"-> unknown node {node.id}")
                    elif fb.root.union_type == ThymioFB.MESSAGE_TYPE_SCRATCHPAD_UPDATE:
                        request_id = FlatBuffer.field_val(fb.root.union_data[0].fields[0], 0)
                        scratchpad_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[1])
                        group_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[2])
                        node_id_str = ThymioFB.bytes_to_id_str(fb.root.union_data[0].fields[3])
                        language = FlatBuffer.field_val(fb.root.union_data[0].fields[4], ThymioFB.PROGRAMMING_LANGUAGE_ASEBA)
                        text = FlatBuffer.field_val(fb.root.union_data[0].fields[5], "")
                        name = FlatBuffer.field_val(fb.root.union_data[0].fields[6], "")
                        deleted = FlatBuffer.field_val(fb.root.union_data[0].fields[7], False)
                        print(f"Scratchpad language={language} name={name} deleted={deleted}:\n{text}")
                    else:
                        print("Not handled")


            except TimeoutError:
                pass


class Server:

    PORT = 10000

    def __init__(self, port=None):
        self.port = port or Server.PORT
        self.socket_listener = None
        self.nodes = set()

    def start(self):
        self.stop()
        self.socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_listener.bind(('', self.port))
        self.socket_listener.listen(5)

    def accept(self):
        socket_client, address = self.socket_listener.accept()
        thr = ServerThread(self, socket_client, address)
        thr.start()

    def stop(self):
        if self.socket_listener is not None:
            self.socket_listener.close()
            self.socket_listener = None

    def findNode(self, node_id_str):
        for node in self.nodes:
            if node.id == node_id_str:
                return node
