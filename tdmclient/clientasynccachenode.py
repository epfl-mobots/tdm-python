# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ClientAsyncNode
import types


class ArrayCache:

    def __init__(self, node, var_name):
        self.node = node
        self.var_name = var_name

    def __repr__(self):
        return f"Node array variable {self.var_name}[{len(self.node.var[self.var_name])}]"

    def __getitem__(self, key):
        return self.node.var[self.var_name][key]

    def __setitem__(self, key, value):
        self.node.var[self.var_name][key] = value
        self.node.mark_change(self.var_name)


class VarPrefix:

    def __init__(self, node, prefix=""):
        # assign attributes without calling VarPrefix.__setattr__
        object.__setattr__(self, "node", node)
        object.__setattr__(self, "prefix", prefix)

    def __getattr__(self, key):
        name = self.prefix + key
        if name in self.node.var:
            return self.node.__getitem__(name)
        else:
            # not there yet
            return VarPrefix(self.node, name + ".")

    def __setattr__(self, key, value):
        name = self.prefix + key
        self.node.__setitem__(name, value)


class TDMIncompatibleVarSizeError(Exception):
    """Assignment of value whose size is incompatible with variable.
    """

    def __init__(self, name, size, value_size):
        super().__init__()
        self.message = f"Incompatible size (assignment of a list of size {value_size} to {name}[{size}])"

    def __str__(self):
        return self.message


class ClientAsyncCacheNode(ClientAsyncNode):

    def __init__(self, thymio, node_dict):
        super(ClientAsyncCacheNode, self).__init__(thymio, node_dict)
        self.var = {}
        self.var_to_send = {}
        self.v = VarPrefix(self)

        def on_variables_changed(node, variables):
            self.var = {**self.var, **variables}

        self.add_variables_changed_listener(on_variables_changed)

    def __getitem__(self, key):
        v = self.var[key]
        if len(v) == 1:
            # direct access for scalar
            return v[0]
        else:
            # via object for array, to cache changes
            return ArrayCache(self, key)

    def __setitem__(self, key, value):
        var_len = len(self.var[key])
        if isinstance(value, int):
            # scalar
            if var_len != 1:
                raise TDMIncompatibleVarSizeError(key, var_len, 1)
            self.var[key] = [value]
        else:
            # list
            if var_len != len(value):
                raise TDMIncompatibleVarSizeError(key, var_len, 1)
            self.var[key] = value
        self.mark_change(key)

    @types.coroutine
    def wait_for_variables(self, var_set=None):
        """Wait until the specified variables, or all of them, have been received.
        """

        # make sure variables are watched
        if not (self.watch_flags & self.thymio.WATCHABLE_INFO_VARIABLES):
            yield from self.watch(variables=True)

        if var_set is None:
            # variables in vm description
            if self.vm_description is None:
                # not retrieved yet
                yield from self.get_vm_description()
            var_set = set(self.vm_description["variables"].keys())

        while not set(self.var).issuperset(var_set):
            if not self.thymio.process_waiting_messages():
                yield from self.thymio.sleep(self.thymio.DEFAULT_SLEEP)
            else:
                yield

    def mark_change(self, var_name):
        self.var_to_send[var_name] = self.var[var_name]

    def flush(self):
        # send new variable values
        self.send_set_variables(self.var_to_send)
        # process waiting messages, possibly changing self.var
        self.thymio.process_waiting_messages()
        # overwrite variables just sent in case they've been replaced by older values
        self.var = {**self.var, **self.var_to_send}
        self.var_to_send = {}
