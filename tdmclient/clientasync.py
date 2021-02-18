# Yves Piguet, Feb 2021

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
    def sleep(self, duration):
        t0 = monotonic()
        print("t0", t0)
        while duration < 0 or monotonic() < t0 + duration:
            self.process_waiting_messages()
            sleep(self.DEFAULT_SLEEP
                  if duration < 0
                  else max(min(self.DEFAULT_SLEEP, t0 + duration - monotonic()),
                           self.DEFAULT_SLEEP / 1e3))
            yield
        print("t end", monotonic())

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
    def lock_node(self, node_id_str):
        result = None
        done = False
        def notify(r):
            nonlocal result
            nonlocal done
            result = r
            done = True
        self.send_lock_node(node_id_str, request_id_notify=notify)
        while not done:
            yield
            sleep(self.DEFAULT_SLEEP)
            self.process_waiting_messages()
        return result

    @types.coroutine
    def unlock_node(self, node_id_str):
        result = None
        done = False
        def notify(r):
            nonlocal result
            nonlocal done
            result = r
            done = True
        self.send_unlock_node(node_id_str, request_id_notify=notify)
        while not done:
            yield
            sleep(self.DEFAULT_SLEEP)
            self.process_waiting_messages()
        return result

    @types.coroutine
    def compile(self, node_id_str, program, load=True):
        result = None
        done = False
        def notify(r):
            nonlocal result
            nonlocal done
            result = r
            done = True
        self.send_program(node_id_str, program, load, request_id_notify=notify)
        while not done:
            yield
            sleep(self.DEFAULT_SLEEP)
            self.process_waiting_messages()
        return result

    @types.coroutine
    def run(self, node_id_str):
        result = None
        done = False
        def notify(r):
            nonlocal result
            nonlocal done
            result = r
            done = True
        self.set_vm_execution_state(node_id_str, 1, request_id_notify=notify)
        while not done:
            yield
            sleep(self.DEFAULT_SLEEP)
            self.process_waiting_messages()
        return result

    @staticmethod
    def run_async_program(prog):
        co = prog()
        try:
            while True:
                co.send(None)
        except StopIteration:
            pass
