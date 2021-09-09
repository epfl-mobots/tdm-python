# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from time import sleep, monotonic
import tdmclient
import types


class ClientAsync(tdmclient.Client):

    DEFAULT_SLEEP = 0.1

    def __init__(self, node_class=None, **kwargs):
        super(ClientAsync, self).__init__(**kwargs)
        self.node_class = node_class or tdmclient.ClientAsyncCacheNode

    def create_node(self, node_dict):
        return self.node_class(self, node_dict)

    @staticmethod
    def filter_nodes(nodes, node_id=None, node_name=None):
        for node in nodes:
            if ((node_id is None or node_id == node.id_str) and
                (node_name is None or
                 "name" in node.props and node_name == node.props["name"])):
                yield node

    def first_node(self, **kwargs):
        """First matching node if there is one.
        """
        for node in self.filter_nodes(self.nodes, **kwargs):
            return node

    @types.coroutine
    def sleep(self, duration=-1, wake=None):
        t0 = monotonic()
        while duration < 0 or monotonic() < t0 + duration:
            self.process_waiting_messages()
            sleep(self.DEFAULT_SLEEP
                  if duration < 0
                  else max(min(self.DEFAULT_SLEEP, t0 + duration - monotonic()),
                           self.DEFAULT_SLEEP / 1e3))
            if wake is not None and wake():
                break
            yield

    @types.coroutine
    def wait_for_node(self, **kwargs):
        while True:
            if self.process_waiting_messages():
                node = self.first_node(**kwargs)
                if node is not None:
                    return node
            else:
                sleep(self.DEFAULT_SLEEP)
            yield

    @types.coroutine
    def wait_for_status(self, expected_status, **kwargs):
        """Wait until the first node has the specified status.
        """
        while True:
            if self.process_waiting_messages():
                node = self.first_node(**kwargs)
                if node is not None and node.status == expected_status:
                    return
            else:
                sleep(self.DEFAULT_SLEEP)
            yield

    @types.coroutine
    def wait_for_status_set(self, expected_status_set, **kwargs):
        """Wait until the first node has one of the specified statuses.
        """
        while True:
            if self.process_waiting_messages():
                node = self.first_node(**kwargs)
                if node is not None and node.status in expected_status_set:
                    return
            else:
                sleep(self.DEFAULT_SLEEP)
            yield

    @types.coroutine
    def lock(self, wait_for_busy_node=False, **kwargs):
        """Lock the first available node matching the selection criteria and
        return it.

        Keyword arguments:
            wait_for_busy_node: whether to wait until a busy node becomes available
            node_id: node id (string or None)
            node_name: robot name (string or None)

        Should be used in a "with" construct which will manage the unlocking.
        """

        yield from self.wait_for_status_set(
            {self.NODE_STATUS_AVAILABLE} if wait_for_busy_node
            else {self.NODE_STATUS_AVAILABLE, self.NODE_STATUS_BUSY}
        )
        node = self.first_node(**kwargs)
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
