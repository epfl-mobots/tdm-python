# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from time import sleep, monotonic
from tdmclient import ThymioFB, Client, ClientNode
import types


class ClientAsyncNode(ClientNode):

    def __init__(self, thymio, node_dict):

        super(ClientAsyncNode, self).__init__(thymio, node_dict)

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
        self.send_unlock_node()

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
        result = yield from self.thymio.send_msg_and_get_result(
            lambda notify:
                self.watch_node(flags, request_id_notify=notify)
        )
        return result


class ClientAsync(Client):

    DEFAULT_SLEEP = 0.1

    def __init__(self, **kwargs):
        super(ClientAsync, self).__init__(**kwargs)

    def create_node(self, node_dict):
        return ClientAsyncNode(self, node_dict)

    def first_node(self):
        return self.nodes[0] if len(self.nodes) > 0 else None

    @types.coroutine
    def sleep(self, duration=-1):
        t0 = monotonic()
        while duration < 0 or monotonic() < t0 + duration:
            self.process_waiting_messages()
            sleep(self.DEFAULT_SLEEP
                  if duration < 0
                  else max(min(self.DEFAULT_SLEEP, t0 + duration - monotonic()),
                           self.DEFAULT_SLEEP / 1e3))
            yield

    @types.coroutine
    def wait_for_node(self):
        while True:
            if self.process_waiting_messages():
                node = self.first_node()
                if node is not None:
                    return node
            else:
                sleep(self.DEFAULT_SLEEP)
            yield

    @types.coroutine
    def wait_for_status(self, expected_status):
        """Wait until the first node has the specified status.
        """
        while True:
            if self.process_waiting_messages():
                node = self.first_node()
                if node is not None and node.status == expected_status:
                    return
            else:
                sleep(self.DEFAULT_SLEEP)
            yield

    @types.coroutine
    def wait_for_status_set(self, expected_status_set):
        """Wait until the first node has one of the specified statuses.
        """
        while True:
            if self.process_waiting_messages():
                node = self.first_node()
                if node is not None and node.status in expected_status_set:
                    return
            else:
                sleep(self.DEFAULT_SLEEP)
            yield

    @types.coroutine
    def lock(self):
        """Lock the first available node and return it.

        Should be used in a "with" construct which will manage the unlocking.
        """

        yield from self.wait_for_status(self.NODE_STATUS_AVAILABLE)
        node = self.first_node()
        result = yield from node.lock_node()
        if result is not None:
            raise Exception("Node lock error")
        return node

    @types.coroutine
    def send_msg_and_get_result(self, send_fun):
        """Call a function which sends a message and wait for its reply.

        Parameter: send_fun(request_id_notify)
        """

        result = None
        done = False

        def notify(r):
            nonlocal result
            nonlocal done
            result = r
            done = True

        send_fun(notify)
        while not done:
            yield
            sleep(self.DEFAULT_SLEEP)
            self.process_waiting_messages()
        return result

    @staticmethod
    def step_coroutine(co):
        """Perform one step of a coroutine (the result of calling an async function).
        Return True if the coroutine is still running, False when it has terminated.
        """
        try:
            co.send(None)
            return True
        except StopIteration:
            return False

    @staticmethod
    def run_async_program(prog):
        """Run an async program (typically the name of an async def) until it terminates.
        """

        co = prog()
        try:
            while True:
                co.send(None)
        except StopIteration:
            pass

    @staticmethod
    def aw(co):
        """Like await, but also valid outside a function, typically in the repl.
        """

        r = None

        async def prog():
            nonlocal r
            r = await co

        ClientAsync.run_async_program(prog)
        return r
