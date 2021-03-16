# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from time import sleep, monotonic
from tdmclient import Client
import types


class ClientAsync(Client):

    DEFAULT_SLEEP = 0.1

    def __init__(self, **kwargs):
        super(ClientAsync, self).__init__(**kwargs)

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
        while True:
            if self.process_waiting_messages():
                node = self.first_node()
                if node is not None:
                    status = node["status"]
                    if status == expected_status:
                        return
            else:
                sleep(self.DEFAULT_SLEEP)
            yield

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

    @types.coroutine
    def lock_node(self, node_id_str):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.send_lock_node(node_id_str, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def unlock_node(self, node_id_str):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.send_unlock_node(node_id_str, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def lock(self, node_id_str=None):
        """Lock the specified node and return its node id as a string.
        Without node id argument, wait until the first node is available
        and use it.

        Should be used in a "with" construct which will manage the unlocking.
        """

        class Lock:

            def __init__(self, tdm, node_id_str):
                self.tdm = tdm
                self.node_id_str = node_id_str

            def __enter__(self):
                return self.node_id_str

            def __exit__(self, type, value, traceback):
                self.tdm.send_unlock_node(node_id_str)


        if node_id_str is None:
            yield from self.wait_for_status(self.NODE_STATUS_AVAILABLE)
            node_id_str = self.first_node()["node_id_str"]
        result = yield from self.lock_node(node_id_str)
        if result is not None:
            raise Exception("Node lock error")
        return Lock(self, node_id_str)

    @types.coroutine
    def register_events(self, node_id_str, events):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.send_register_events(node_id_str, events, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def set_variables(self, node_id_str, var_dict):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.send_set_variables(node_id_str, var_dict, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def compile(self, node_id_str, program, load=True):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.send_program(node_id_str, program, load, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def run(self, node_id_str):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.set_vm_execution_state(node_id_str, self.VM_EXECUTION_STATE_COMMAND_RUN, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def stop(self, node_id_str):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.set_vm_execution_state(node_id_str, self.VM_EXECUTION_STATE_COMMAND_STOP, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def flash(self, node_id_str):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.set_vm_execution_state(node_id_str, self.VM_EXECUTION_STATE_COMMAND_WRITE_PROGRAM_TO_DEVICE_MEMORY, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def set_scratchpad(self, node_id_str, program):
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.send_set_scratchpad(node_id_str, program, request_id_notify=notify)
        )
        return result

    @types.coroutine
    def watch(self, node_id_str, flags=0, variables=False, events=False):
        flags |= ((self.WATCHABLE_INFO_VARIABLES if variables else 0) |
                  (self.WATCHABLE_INFO_EVENTS if events else 0))
        result = yield from self.send_msg_and_get_result(
            lambda notify:
                self.watch_node(node_id_str, flags, request_id_notify=notify)
        )
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
