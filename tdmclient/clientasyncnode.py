# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ThymioFB, ClientNode
import types


class ClientAsyncNode(ClientNode):

    def __init__(self, thymio, node_dict):

        super(ClientAsyncNode, self).__init__(thymio, node_dict)

        # current watch flags
        self.watch_flags = 0

    @types.coroutine
    def get_vm_description(self):
        """Get the VM description.
        """

        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_request_vm_description(request_id_notify=notify)
        )
        return result

    @types.coroutine
    def lock_node(self):
        """Lock the node and return the error code (None for success).
        """

        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_lock_node(request_id_notify=notify)
        )
        return result

    @types.coroutine
    def unlock(self):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_unlock_node(request_id_notify=notify)
        )
        return result

    @types.coroutine
    def lock(self):
        """Lock itself.

        Should be used in a "with" construct which will manage the unlocking.
        """

        result = yield from self.lock_node()
        if result is not None:
            raise Exception("Node lock error")
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.send_unlock_node(ignore_disconnected_error=True)

    @types.coroutine
    def rename(self, name):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_rename_node(name, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def register_events(self, events):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_register_events(events, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def send_events(self, event_dict):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_send_events(event_dict, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def set_variables(self, var_dict):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_set_variables(var_dict, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def compile(self, program, load=True):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_program(program, load, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def run(self):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.set_vm_execution_state(ThymioFB.VM_EXECUTION_STATE_COMMAND_RUN, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def stop(self):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.set_vm_execution_state(ThymioFB.VM_EXECUTION_STATE_COMMAND_STOP, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def flash(self):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.set_vm_execution_state(ThymioFB.VM_EXECUTION_STATE_COMMAND_WRITE_PROGRAM_TO_DEVICE_MEMORY, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def set_scratchpad(self, program):
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.send_set_scratchpad(program, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def watch(self, flags=0, variables=False, events=False):
        flags |= ((ThymioFB.WATCHABLE_INFO_VARIABLES if variables else 0) |
                  (ThymioFB.WATCHABLE_INFO_EVENTS if events else 0))
        if (self.watch_flags | flags) != self.watch_flags:
            self.watch_flags |= flags
            result = yield from self.thymio.send_msg_and_get_result(
                lambda notify:
                    self.watch_node(flags, request_id_notify=notify)
            )
            return result

    @types.coroutine
    def unwatch(self, flags=0, variables=False, events=False):
        flags |= ((ThymioFB.WATCHABLE_INFO_VARIABLES if variables else 0) |
                  (ThymioFB.WATCHABLE_INFO_EVENTS if events else 0))
        if (self.watch_flags & ~flags) != self.watch_flags:
            self.watch_flags &= ~flags
            result = yield from self.thymio.send_msg_and_get_result(
                lambda notify:
                    self.watch_node(flags, request_id_notify=notify)
            )
            return result
