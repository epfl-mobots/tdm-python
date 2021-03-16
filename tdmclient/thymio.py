# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Thymio-related flatbuffer for Thymio Device Manager
Author: Yves Piguet, EPFL
"""


from tdmclient import FlatBuffer, Union, Table


class ThymioFB:

    MESSAGE_TYPE_CONNECTION_HANDSHAKE = 1
    MESSAGE_TYPE_DEVICE_MANAGER_SHUTDOWN_REQUEST = 2
    MESSAGE_TYPE_REQUEST_LIST_OF_NODES = 3
    MESSAGE_TYPE_REQUEST_NODE_ASEBA_VM_DESCRIPTION = 4
    MESSAGE_TYPE_LOCK_NODE = 5
    MESSAGE_TYPE_UNLOCK_NODE = 6
    MESSAGE_TYPE_RENAME_NODE = 7
    MESSAGE_TYPE_COMPILE_AND_LOAD_CODE_ON_VM = 8
    MESSAGE_TYPE_NODES_CHANGED = 9
    MESSAGE_TYPE_NODE_ASEBA_VM_DESCRIPTION = 10
    MESSAGE_TYPE_REQUEST_COMPLETED = 11
    MESSAGE_TYPE_ERROR = 12
    MESSAGE_TYPE_COMPILATION_RESULT_FAILURE = 13
    MESSAGE_TYPE_COMPILATION_RESULT_SUCCESS = 14
    MESSAGE_TYPE_WATCH_NODE = 15
    MESSAGE_TYPE_VARIABLES_CHANGED = 16
    MESSAGE_TYPE_SET_VARIABLES = 17
    MESSAGE_TYPE_EVENTS_DESCRIPTIONS_CHANGED = 18
    MESSAGE_TYPE_REGISTER_EVENTS = 19
    MESSAGE_TYPE_SEND_EVENTS = 20
    MESSAGE_TYPE_EVENTS_EMITTED = 21
    MESSAGE_TYPE_SET_BREAKPOINTS = 22
    MESSAGE_TYPE_SET_BREAKPOINTS_RESPONSE = 23
    MESSAGE_TYPE_SET_VM_EXECUTION_STATE = 24
    MESSAGE_TYPE_VM_EXECUTION_STATE_CHANGED = 25
    MESSAGE_TYPE_SCRATCHPAD_UPDATE = 26
    MESSAGE_TYPE_FIRMWARE_UPGRADE_REQUEST = 27
    MESSAGE_TYPE_FIRMWARE_UPGRADE_STATUS = 28
    MESSAGE_TYPE_PING = 29
    MESSAGE_TYPE_ENABLE_THYMIO2_PAIRING_MODE = 30
    MESSAGE_TYPE_THYMIO2_WIRELESS_DONGLES_CHANGED = 31
    MESSAGE_TYPE_THYMIO2_WIRELESS_DONGLE_PAIRING_REQUEST = 32
    MESSAGE_TYPE_THYMIO2_WIRELESS_DONGLE_PAIRING_RESPONSE = 33
    MESSAGE_TYPE_COMPILE_AND_SAVE = 34
    MESSAGE_TYPE_SAVE_BYTECODE = 35

    NODE_TYPE_THYMIO2 = 0
    NODE_TYPE_THYMIO2WIRELESS = 1
    NODE_TYPE_SIMULATED_THYMIO2 = 2
    NODE_TYPE_DUMMY_NODE = 3
    NODE_TYPE_UNKNOWN_TYPE = 4

    NODE_CAPABILITY_RENAME = 0x1
    NODE_CAPABILITY_FORCE_RESET_AND_STOP = 0x2
    NODE_CAPABILITY_FIRMWARE_UPGRADE = 0x4

    NODE_STATUS_UNKNOWN = 0
    NODE_STATUS_CONNECTED = 1
    NODE_STATUS_AVAILABLE = 2
    NODE_STATUS_BUSY = 3
    NODE_STATUS_READY = 4
    NODE_STATUS_DISCONNECTED = 5

    ERROR_NO_ERROR = 0
    ERROR_UNKNOWN = 1
    ERROR_UNKNOWN_NODE = 2
    ERROR_NODE_BUSY = 3
    ERROR_UNSUPPORTED_VARIABLE_TYPE = 4
    ERROR_THYMIO2_PAIRING_WRITE_DONGLE_FAILED = 5
    ERROR_THYMIO2_PAIRING_WRITE_ROBOT_FAILED = 6

    WATCHABLE_INFO_STOP_MONITORING = 0
    WATCHABLE_INFO_VARIABLES = 0x1
    WATCHABLE_INFO_EVENTS = 0x2
    WATCHABLE_INFO_VM_EXECUTION_STATE = 0x4
    WATCHABLE_INFO_SHARED_EVENTS_DESCRIPTION = 0x8
    WATCHABLE_INFO_SHARED_VARIABLES = 0x10
    WATCHABLE_INFO_SCRATCHPADS = 0x20

    PROGRAMMING_LANGUAGE_ASEBA = 1
    PROGRAMMING_LANGUAGE_AESL = 2

    COMPILATION_OPTION_NONE = 1 # according to thymio.fbs
    COMPILATION_OPTION_LOAD_ON_TARGET = 2
    COMPILATION_OPTION_FETCH_BYTECODE = 4

    VM_EXECUTION_STATE_COMMAND_STOP = 0
    VM_EXECUTION_STATE_COMMAND_RUN = 1
    VM_EXECUTION_STATE_COMMAND_STEP = 2
    VM_EXECUTION_STATE_COMMAND_STEP_TO_NEXT_LINE = 3
    VM_EXECUTION_STATE_COMMAND_PAUSE = 4
    VM_EXECUTION_STATE_COMMAND_RESET = 5
    VM_EXECUTION_STATE_COMMAND_REBOOT = 6
    VM_EXECUTION_STATE_COMMAND_SUSPEND = 7
    VM_EXECUTION_STATE_COMMAND_WRITE_PROGRAM_TO_DEVICE_MEMORY = 8

    VM_EXECUTION_STATE_STOPPED = 0
    VM_EXECUTION_STATE_RUNNING = 1
    VM_EXECUTION_STATE_PAUSED = 2

    def __init__(self, debug=0):

        self.debug = debug

        self.protocol_version = None
        self.localhost_peer = None
        self.nodes = []
        self.last_request_id = 0
        self.request_id_notify_dict = {}

        self.on_nodes_changed = None
        self.on_variables_changed = None

    def create_message(self, msg, schema=None):
        fb = FlatBuffer()
        if schema is None:
            fb.load_from_native_type(msg)
        else:
            fb.load_with_schema(msg, schema)
        encoded_fb = fb.encode()

        return encoded_fb

    def next_request_id(self, request_id_notify=None):
        self.last_request_id += 1
        if request_id_notify is not None:
            self.request_id_notify_dict[self.last_request_id] = request_id_notify
        return self.last_request_id

    def get_node_id(self, node_id_str):
        for node in self.nodes:
            if node["node_id_str"] == node_id_str:
                return node["node_id"]
        raise Exception("node id not found")

    SCHEMA = """
        // see https://github.com/Mobsya/aseba/blob/master/aseba/flatbuffers/thymio.fbs
        // root object: union AnyMessage
        U(
            // ConnectionHandshake
            T(iiibb)
            // DeviceManagerShutdownRequest
            T(i)
            // RequestListOfNodes
            T()
            // RequestNodeAsebaVMDescription
            T(iT(*u))
            // LockNode
            T(iT(*u))
            // UnlockNode
            T(iT(*u))
            // RenameNode
            T(iT(*u)s)
            // CompileAndLoadCodeOnVM
            T(iT(*u)isi)
            // NodesChanged
            T(
                // nodes: [Node]
                *T(
                    // node_id: NodeId
                    T(*u)
                    // group_id: NodeId
                    T(*u)
                    // status: NodeStatus
                    i
                    // type: NodeType
                    i
                    // name: string
                    s
                    // capabilities: ulong
                    l
                    // fw_version: string
                    s
                    // latest_fw_version: string
                    s
                )
            )
            // NodeAsebaVMDescription
            T(iT(*u)iii*T(2si)*T(2ss)*T(2ss*T(si)))
            // RequestCompleted
            T(i)
            // Error
            T(ii)
            // CompilationResultFailure
            T(isiii)
            // CompilationResultSuccess
            T(iiiii)
            // WatchNode
            T(iT(*u)i)
            // VariablesChanged
            T(T(*u)*T(sx)l)
            // SetVariables
            T(iT(*u)*T(sx))
            // EventsDescriptionsChanged
            T(T(*u)*T(sii))
            // RegisterEvents
            T(iT(*u)*T(sii))
            // SendEvents
            T(iT(*u)*T(sx))
            // EventsEmitted
            T(T(*u)*T(sx)l)
            // SetBreakpoints
            T(iT(*u)*T(i))
            // SetBreakpointsResponse
            T(ii*T(i))
            // SetVMExecutionState
            T(iT(*u)2)
            // VMExecutionStateChanged
            T(T(*u)2iis)
            // ScratchpadUpdate
            T(iT(*u)T(*u)T(*u)issb)
            // FirmwareUpgradeRequest
            T(iT(*u))
            // FirmwareUpgradeStatus
            T(iT(*u)d)
            // Ping
            T()
            // EnableThymio2PairingMode
            T(b)
            // Thymio2WirelessDonglesChanged
            T(*T(T(*u)22b))
            // Thymio2WirelessDonglePairingRequest
            T(iT(*u)T(*u)2b)
            // Thymio2WirelessDonglePairingResponse
            T(i2b)
            // CompileAndSave
            T(iT(*u)isi)
            // SaveBytecode
            T(iT(*u)s)
        )
    """

    def create_msg_handshake(self):
        return self.create_message((
            self.MESSAGE_TYPE_CONNECTION_HANDSHAKE,
            ()
        ), self.SCHEMA)

    def create_msg_lock_node(self, node_id_str, **kwargs):
        return self.create_message((
            self.MESSAGE_TYPE_LOCK_NODE,
            (
                self.next_request_id(**kwargs),
                (
                    self.get_node_id(node_id_str),
                ),
            )
        ), self.SCHEMA)

    def create_msg_unlock_node(self, node_id_str, **kwargs):
        return self.create_message((
            self.MESSAGE_TYPE_UNLOCK_NODE,
            (
                self.next_request_id(**kwargs),
                (
                    self.get_node_id(node_id_str),
                ),
            )
        ), self.SCHEMA)

    def create_msg_program(self, node_id_str, program, load=True, **kwargs):
        return self.create_message((
            self.MESSAGE_TYPE_COMPILE_AND_LOAD_CODE_ON_VM,
            (
                self.next_request_id(**kwargs),
                (
                    self.get_node_id(node_id_str),
                ),
                self.PROGRAMMING_LANGUAGE_ASEBA,
                program,
                self.COMPILATION_OPTION_LOAD_ON_TARGET
                    if load
                    else self.COMPILATION_OPTION_NONE,
            )
        ), self.SCHEMA)

    def create_msg_scratchpad_update(self, node_id_str, program, **kwargs):
        return self.create_message((
            self.MESSAGE_TYPE_SCRATCHPAD_UPDATE,
            (
                self.next_request_id(**kwargs),
                (
                    self.get_node_id(node_id_str),
                ),
                None,
                (
                    self.get_node_id(node_id_str),
                ),
                self.PROGRAMMING_LANGUAGE_ASEBA,
                program,
            )
        ), self.SCHEMA)

    def create_msg_set_vm_execution_state(self, node_id_str, state, **kwargs):
        return self.create_message((
            self.MESSAGE_TYPE_SET_VM_EXECUTION_STATE,
            (
                self.next_request_id(**kwargs),
                (
                    self.get_node_id(node_id_str),
                ),
                state
            )
        ), self.SCHEMA)

    def create_msg_watch_node(self, node_id_str, flags, **kwargs):
        return self.create_message((
            self.MESSAGE_TYPE_WATCH_NODE,
            (
                self.next_request_id(**kwargs),
                (
                    self.get_node_id(node_id_str),
                ),
                flags
            )
        ), self.SCHEMA)

    def create_msg_register_events(self, node_id_str, events, **kwargs):
        return self.create_message((
            self.MESSAGE_TYPE_REGISTER_EVENTS,
            (
                self.next_request_id(**kwargs),
                (
                    self.get_node_id(node_id_str),
                ),
                [
                    (
                        event[0], # name (str)
                        event[1], # fixed size (int)
                        0, # index (int)
                    )
                    for event in events
                ]
            )
        ), self.SCHEMA)

    def create_msg_set_variables(self, node_id_str, var_dict, **kwargs):
        return self.create_message((
            self.MESSAGE_TYPE_SET_VARIABLES,
            (
                self.next_request_id(**kwargs),
                (
                    self.get_node_id(node_id_str),
                ),
                [
                    (
                        name,
                        var_dict[name],
                    )
                    for name in var_dict
                ]
            )
        ), self.SCHEMA)

    def process_message(self, msg):

        def field_val(f, default):
            return f[0] if f is not None else default

        def bytes_to_hexa(f):
            if f is None:
                return None
            else:
                return "".join([f"{b if type(b) is int else ord(b):02x}" for b in f[0].fields[0][0]])

        fb = FlatBuffer()
        fb.parse(msg, self.SCHEMA)
        if self.debug >= 3:
            fb.dump()
        if type(fb.root) is Union:
            if fb.root.union_type == self.MESSAGE_TYPE_PING:
                pass
            elif fb.root.union_type == self.MESSAGE_TYPE_CONNECTION_HANDSHAKE:
                self.protocol_version = field_val(fb.root.union_data[0].fields[1], 1)
                self.localhost_peer = field_val(fb.root.union_data[0].fields[4], False)
            elif fb.root.union_type == self.MESSAGE_TYPE_NODES_CHANGED:
                if fb.root.union_data[0] is not None:
                    nodes = fb.root.union_data[0].fields[0][0]
                    self.nodes = [
                        {
                            "node_id":
                                None if node.fields[0] is None
                                else node.fields[0][0].fields[0][0] if type(node.fields[0][0].fields[0][0]) is bytes
                                else b"".join(node.fields[0][0].fields[0][0]),
                            "node_id_str": bytes_to_hexa(node.fields[0]),
                            "group_id": field_val(node.fields[1], None),
                            "status": field_val(node.fields[2], -1),
                            "type": field_val(node.fields[3], -1),
                            "name": field_val(node.fields[4], ""),
                            "capabilities": field_val(node.fields[5], 0),
                            "fw_version": field_val(node.fields[6], None),
                        }
                        for node in nodes
                    ]
                    if self.on_nodes_changed is not None:
                        self.on_nodes_changed(self.nodes)
                    if self.debug >= 1:
                        print("NodesChanged",
                              ", ".join(f"{node['node_id_str']}: status={node['status']}" for node in self.nodes))
            elif fb.root.union_type == self.MESSAGE_TYPE_REQUEST_COMPLETED:
                request_id = field_val(fb.root.union_data[0].fields[0], 0)
                if request_id in self.request_id_notify_dict:
                    self.request_id_notify_dict[request_id](None)
                    del self.request_id_notify_dict[request_id]
                    if self.debug >= 1:
                        print("ok")
                elif self.debug >= 1:
                    print(f"ok request_id={request_id} (ignored)")
            elif fb.root.union_type == self.MESSAGE_TYPE_ERROR:
                request_id = field_val(fb.root.union_data[0].fields[0], 0)
                error_code = field_val(fb.root.union_data[0].fields[1], 0)
                if request_id in self.request_id_notify_dict:
                    self.request_id_notify_dict[request_id]({"error_code": error_code})
                    del self.request_id_notify_dict[request_id]
                    if self.debug >= 1:
                        print(f"error {error_code}")
                elif self.debug >= 1:
                    print(f"error {error_code} request_id={request_id} (ignored)")
            elif fb.root.union_type == self.MESSAGE_TYPE_COMPILATION_RESULT_FAILURE:
                request_id = field_val(fb.root.union_data[0].fields[0], 0)
                error_msg = field_val(fb.root.union_data[0].fields[1], "")
                error_line = field_val(fb.root.union_data[0].fields[3], 0)
                error_col = field_val(fb.root.union_data[0].fields[4], 0)
                if request_id in self.request_id_notify_dict:
                    self.request_id_notify_dict[request_id]({
                        "error_msg": error_msg,
                        "error_line": error_line,
                        "error_col": error_col,
                    })
                    del self.request_id_notify_dict[request_id]
                    if self.debug >= 1:
                        print(f"compilation error: {error_msg}")
                elif self.debug >= 1:
                    print(f"compilation error: {error_msg} request_id={request_id} (ignored)")
            elif fb.root.union_type == self.MESSAGE_TYPE_COMPILATION_RESULT_SUCCESS:
                request_id = field_val(fb.root.union_data[0].fields[0], 0)
                if request_id in self.request_id_notify_dict:
                    self.request_id_notify_dict[request_id](None)
                    del self.request_id_notify_dict[request_id]
                    if self.debug >= 1:
                        print("compilation ok")
                elif self.debug >= 1:
                    print(f"compilation ok request_id={request_id} (ignored)")
            elif fb.root.union_type == self.MESSAGE_TYPE_VARIABLES_CHANGED:
                node_id_str = bytes_to_hexa(fb.root.union_data[0].fields[0])
                variables = {
                    v.fields[0][0]: v.fields[1][0]
                    for v in fb.root.union_data[0].fields[1][0]
                }
                if self.on_variables_changed is not None:
                    self.on_variables_changed(node_id_str, {"variables": variables})
                if self.debug >= 1:
                    print(f"variables of node {node_id_str} changed")
                    if self.debug >= 2:
                        for name in variables:
                            print(name, variables[name])
            elif fb.root.union_type == self.MESSAGE_TYPE_EVENTS_DESCRIPTIONS_CHANGED:
                node_or_group_id = bytes_to_hexa(fb.root.union_data[0].fields[0])
                if fb.root.union_data[0].fields[1] is not None:
                    event_size = {
                        e.fields[0][0]: field_val(e.fields[1], 0)
                        for e in fb.root.union_data[0].fields[1][0]
                    }
                    event_index = {
                        e.fields[0][0]: field_val(e.fields[2], 0)
                        for e in fb.root.union_data[0].fields[1][0]
                    }
                else:
                    event_size = []
                    event_index = []
                if self.debug >= 1:
                    print(f"event sizes of node or group {node_or_group_id} changed")
                    if self.debug >= 2:
                        print("\n".join([
                            f"{name}[{event_size[name]}]" for name in event_size
                        ]))
            elif fb.root.union_type == self.MESSAGE_TYPE_EVENTS_EMITTED:
                node_id_str = bytes_to_hexa(fb.root.union_data[0].fields[0])
                events = {
                    e.fields[0][0]: e.fields[1][0]
                    for e in fb.root.union_data[0].fields[1][0]
                }
                if self.debug >= 1:
                    print(f"events emitted by node {node_id_str}")
                    if self.debug >= 2:
                        for name in events:
                            print(name,
                                  events[name] if events[name] is not None else "")
            elif fb.root.union_type == self.MESSAGE_TYPE_VM_EXECUTION_STATE_CHANGED:
                node_id_str = bytes_to_hexa(fb.root.union_data[0].fields[0])
                state = field_val(fb.root.union_data[0].fields[1], 0)
                line = field_val(fb.root.union_data[0].fields[2], 0)
                error = field_val(fb.root.union_data[0].fields[3], 0)
                error_msg = field_val(fb.root.union_data[0].fields[4], "")
                if self.debug >= 1:
                    print(f"execution state of node {node_id_str} changed to {state}, line={line}, error={error} {error_msg}")
            elif fb.root.union_type == self.MESSAGE_TYPE_SCRATCHPAD_UPDATE:
                request_id = field_val(fb.root.union_data[0].fields[0], 0)
                scratchpad_id_str = bytes_to_hexa(fb.root.union_data[0].fields[1])
                group_id_str = bytes_to_hexa(fb.root.union_data[0].fields[2])
                node_id_str = bytes_to_hexa(fb.root.union_data[0].fields[3])
                language = field_val(fb.root.union_data[0].fields[4], self.PROGRAMMING_LANGUAGE_ASEBA)
                text = field_val(fb.root.union_data[0].fields[5], "")
                name = field_val(fb.root.union_data[0].fields[6], "")
                deleted = field_val(fb.root.union_data[0].fields[7], False)
                if self.debug >= 1:
                    print(f"scratchpad {scratchpad_id_str} of node {node_id_str} / group {group_id_str} updated")
                    print(text)
            else:
                print(f"Got unprocessed message {fb.root.union_type}")
