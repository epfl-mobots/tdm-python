# Yves Piguet, Jan-Feb 2021

"""
Thymio-related flatbuffer for Thymio Device Manager
Author: Yves Piguet, EPFL
"""


from tdmclient import FlatBuffer, Union, Table


class ThymioFB:

    def __init__(self, debug=False):

        self.debug = debug

        self.protocol_version = None
        self.localhost_peer = None
        self.nodes = []
        self.last_request_id = 0

    def create_message(self, msg, schema=None):
        fb = FlatBuffer()
        if schema is None:
            fb.load_from_native_type(msg)
        else:
            fb.load_with_schema(msg, schema)
        encoded_fb = fb.encode()

        return encoded_fb

    def next_request_id(self):
        self.last_request_id += 1
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
            T(T(*u)*T(s.)l)
            // SetVariables
            T(iT(*u)*T(s.))
            // EventsDescriptionsChanged
            T(T(*u)*T(sii))
            // RegisterEvents
            T(iT(*u)*T(sii))
            // SendEvents
            T(iT(*u)*T(s.))
            // EventsEmitted
            T(T(*u)*T(s.)l)
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
            1, # ConnectionHandshake
            ()
        ), self.SCHEMA)

    def create_msg_lock_node(self, node_id_str):
        return self.create_message((
            5, # LockNode
            (
                self.next_request_id(),
                (
                    self.get_node_id(node_id_str),
                ),
            )
        ), self.SCHEMA)

    def create_msg_unlock_node(self, node_id_str):
        return self.create_message((
            6, # UnlockNode
            (
                self.next_request_id(),
                (
                    self.get_node_id(node_id_str),
                ),
            )
        ), self.SCHEMA)

    def create_msg_program(self, node_id_str, program, load=True):
        return self.create_message((
            8, # CompileAndLoadCodeOnVM
            (
                self.next_request_id(),
                (
                    self.get_node_id(node_id_str),
                ),
                1, # Aseba
                program,
                2 if load else 0, # LoadOnTarget or NoOption
            )
        ), self.SCHEMA)

    def create_msg_set_vm_execution_state(self, node_id_str, state):
        return self.create_message((
            24, # SetVMExecutionState
            (
                self.next_request_id(),
                (
                    self.get_node_id(node_id_str),
                ),
                state
            )
        ), self.SCHEMA)

    def process_message(self, msg):

        def field_val(f, default):
            return f[1] if f is not None else default

        fb = FlatBuffer()
        fb.parse(msg, self.SCHEMA)
        if self.debug:
            fb.dump()
        if type(fb.root) is Union:
            if fb.root.union_type == 1:
                # ConnectionHandshake
                self.protocol_version = field_val(fb.root.union_data[1].fields[1], 1)
                self.localhost_peer = field_val(fb.root.union_data[1].fields[4], False)
            elif fb.root.union_type == 9:
                # NodesChanged
                if fb.root.union_data[1] is not None:
                    nodes = fb.root.union_data[1].fields[0][1]
                    self.nodes = [
                        {
                            "node_id":
                                b"".join(node.fields[0][1].fields[0][1])
                                if node.fields[0] is not None
                                else None,
                            "node_id_str":
                                "".join([f"{ord(b):02x}" for b in node.fields[0][1].fields[0][1]])
                                if node.fields[0] is not None
                                else None,
                            "group_id": field_val(node.fields[1], None),
                            "status": field_val(node.fields[2], -1),
                            "type": field_val(node.fields[3], -1),
                            "name": field_val(node.fields[4], ""),
                            "capabilities": field_val(node.fields[5], 0),
                            "fw_version": field_val(node.fields[6], None),
                        }
                        for node in nodes
                    ]
                    if self.debug:
                        print("NodesChanged", self.nodes)
            elif fb.root.union_type == 11:
                # request completed
                if self.debug:
                    print("ok")
            elif fb.root.union_type == 13:
                # CompilationResultFailure
                error_msg = field_val(fb.root.union_data[1].fields[1], "")
                error_line = field_val(fb.root.union_data[3].fields[1], 0)
                error_col = field_val(fb.root.union_data[4].fields[1], 0)
                if self.debug:
                    print(f"compilation error: {error_msg}")
            elif fb.root.union_type == 14:
                # compilation result success
                if self.debug:
                    print("compilation ok")
            elif fb.root.union_type == 15:
                # compilation result success
                if self.debug:
                    print("compilation error")
            elif fb.root.union_type == 29:
                # ping
                pass
            else:
                print(f"Got message {fb.root.union_type}")
