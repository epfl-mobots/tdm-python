# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import code
import ast
import re
import sys

from tdmclient import ClientAsync, ArrayCache
from tdmclient.atranspiler import ATranspiler
from tdmclient.module_thymio import ModuleThymio
from tdmclient.module_clock import ModuleClock
from tdmclient.atranspiler_warnings import missing_global_decl


class TDMConsole(code.InteractiveConsole):

    def __init__(self,
                 local_var=None,
                 define_functions=True,
                 user_functions=None):
        """New interactive console with synchronization with TDM node.

        Argument:
            local_var -- if not None (dict), synchronized variables are stored in
            local_var; if False (default), they're stored in the TDMConsole's
            globals (should be None for plain cpython repl, get_ipython().user_ns
            for ipython)
        """

        # client and node set in async init
        self.client = None
        self.node = None

        # self.event_data_dict[node_id][event_name] = list of event data
        self.event_data_dict = {}

        def onevent(fun):
            """Function decorator @onevent for event handlers. The event name
            is given by the function name.
            """

            self.onevent_functions.add(fun.__name__)
            return fun

        def sleep(t):
            """Wait for some time.

            Argument:
                t -- time to wait in seconds
            """

            # send and flush all variables which might have been changed
            self.send_variables(self.var_set)

            # wait
            ClientAsync.aw(self.client.sleep(t))

            # fetch all variables which might be used
            self.fetch_variables(self.var_got, node_flush=False)

        def robot_code(language="python"):
            """Gather Python or Aseba source code for the robot.

            Argument:
                language -- "python" (default) or "aseba"
            """

            src = ""

            # robot variables
            for name_a in self.robot_var_set:
                name_py = self.to_python_name(name_a)
                src += f"""{name_py} = {self.local_var[name_py]}
"""

            # onevent
            functions_called = set()
            var_global = set()
            for name in self.onevent_functions:
                src += self.fun_defs[name]["src"]
                functions_called |= self.fun_defs[name]["calls"]
                var_global |= self.fun_defs[name]["global"].difference(self.sync_var)

            # functions called from onevent
            functions_added = self.onevent_functions.copy()
            while True:
                functions_remaining = functions_called.difference(functions_added)
                if len(functions_remaining) == 0:
                    break
                name = list(functions_remaining)[0]
                src += self.fun_defs[name]["src"]
                functions_added.add(name)
                functions_called |= self.fun_defs[name]["calls"]
                var_global |= self.fun_defs[name]["global"].difference(self.sync_var)

            # global variables used by functions
            for name in var_global:
                src += f"""{name} = {self.local_var[name]}
"""

            if language == "aseba":
                # transpile from Python to Aseba
                transpiler = self.transpile(src, True)
                src = transpiler.get_output()
            elif language != "python":
                raise Exception(f"Unsupported language {language}")

            return src

        def robot_code_new():
            """Forget assignments and definitions used to generate robot code.
            """
            self.robot_var_set.clear()
            self.onevent_functions.clear()

        def run(src=None, *,
                language="python",
                warning_missing_global=False,
                wait=None,
                **kwargs):
            """Run program obtained by robot_code on the robot. By default, wait
            to process events until "_exit" is received (call to "exit()" in the
            robot's program), or return immediately if the program doesn't send
            any event.

            Instead of the code obtained by robot_code, the complete source code
            can be passed as a string.

            Other keyword arguments:
                language: "python" (default) or "aseba" (valid only if the
                source code is passed in a string)
                warning_missing_global: if True, display warnings for local
                                        variables which hide global variables
                                        with the same name (default: False)
                robot_id: robot id, to run the program on a specific robot
                robot_name: robot name, to run the program on a specific robot
                robot_index: robot index (0=first=default, 1=second etc.)
            """

            if src is None and language != "python":
                raise Exception("Invalid language for robot code")
            if src is None:
                src = robot_code()
            # compile, load, run, and set scratchpad without checking the result
            try:
                node = self.find_robot(**kwargs) or self.node
                self.run_program(src, [node],
                                 language=language,
                                 warning_missing_global=warning_missing_global,
                                 wait=wait)
            except KeyboardInterrupt:
                # avoid long exception message with stack trace
                print("Interrupted")

        def stop(**kwargs):
            """Stop the program running on the robot.

            Keyword arguments:
                robot_id: robot id, to run the program on a specific robot
                robot_name: robot name, to run the program on a specific robot
                robot_index: robot index (0=first=default, 1=second etc.)
            """
            node = self.find_robot(**kwargs) or self.node
            self.stop_program(node, discard_output=True)

        def get_var(*args):
            """Get robot variables passed as a set or list of names and
            return them in a tuple.
            """
            self.fetch_variables(args)
            return tuple(
                self.local_var[name_py]
                for name_py in args
            )

        def set_var(**kwargs):
            """Set robot variables passed as keyword arguments.
            """
            for name_py in kwargs:
                self.local_var[name_py] = kwargs[name_py]
                self.send_variable(name_py, kwargs[name_py])
            self.flush_variables()

        def clear_event_data(event_name=None, **kwargs):
            """Clear all or named event data.

            Argument:
                event_name: event name (default: all events)
            Keyword argument:
                robot_id: robot id, to run the program on a specific robot
                robot_name: robot name, to run the program on a specific robot
                robot_index: robot index (0=first=default, 1=second etc.)
            """
            node = self.find_robot(**kwargs)
            self.clear_event_data(event_name, node=node)

        def get_event_data(event_name=None, **kwargs):
            """Get list of event data received until now.

            Argument:
                event_name: event name (default: dict of all event lists)
            Keyword argument:
                robot_id: robot id, to run the program on a specific robot
                robot_name: robot name, to run the program on a specific robot
                robot_index: robot index (0=first=default, 1=second etc.)
            """
            node = self.find_robot(**kwargs)
            return self.get_event_data(event_name, node=node)

        def send_event(event_name, *args, **kwargs):
            """Send a custom event to the robot. Arguments can be numbers,
            booleans and/or arrays.

            Keyword arguments:
                robot_id: robot id, to run the program on a specific robot
                robot_name: robot name, to run the program on a specific robot
                robot_index: robot index (0=first=default, 1=second etc.)
            """

            # flatten args
            data = [
                item
                for arg in args
                for item in (arg if isinstance(arg, list) else [arg])
            ]

            node = self.find_robot(**kwargs) or self.node
            node.send_send_events({event_name: data})

        self.functions = {
            "onevent": onevent,
            "sleep": sleep,
            "robot_code": robot_code,
            "robot_code_new": robot_code_new,
            "run": run,
            "stop": stop,
            "get_var": get_var,
            "set_var": set_var,
            "clear_event_data": clear_event_data,
            "get_event_data": get_event_data,
            "send_event": send_event,
            **(user_functions if user_functions is not None else {}),
        }

        if local_var is None:
            # create our own locals
            self.local_var = self.functions.copy() if define_functions else {}
            super().__init__(locals=self.local_var)
        else:
            # put our variables in provided locals
            super().__init__()

            self.local_var = local_var
            if define_functions:
                self.local_var.update(self.functions)

        # from initial node description
        self.sync_var_vm = None
        # completed by variable change messages
        self.sync_var = None

        # for generating source code for robot
        self.robot_var_set = set()
        self.fun_defs = {}
        self.onevent_functions = set()

        # for current command
        self.var_got = set()
        self.var_set = set()

        # enable output upon receiving events
        self.output_enabled = True

    async def init(self, client, node):
        self.client = client
        self.node = node

        await self.node.watch(variables=True)

        # fetch all variables
        await self.node.wait_for_variables()
        sync_var = set()
        for name_a in self.node.vm_description["variables"]:
            value = self.node[name_a]
            if isinstance(value, ArrayCache):
                value = list(value)
            name_py = self.to_python_name(name_a)
            self.local_var[name_py] = value
            sync_var.add(name_py)
        self.sync_var_vm = sync_var
        self.sync_var = sync_var.copy()

        # complete self.sync_var when receiving values for unknown variables
        def update_sync_var(node, variables):
            for name in variables:
                if variables[name] is not None:
                    self.sync_var.add(name)

        self.node.add_variables_changed_listener(update_sync_var)

    @staticmethod
    def transpile(src, import_thymio=True, warning_missing_global=False):
        """Transpile Python source code to Aseba and returns transpiler.

        Argument:
            src -- Python source code
            import_thymio -- if True (default), predefine all Thymio symbols
            warning_missing_global -- if True, display warnings for local
                                      variables which hide global variables
                                      with the same name (default: False)
        """
        transpiler = ATranspiler()
        modules = {
            "thymio": ModuleThymio(transpiler),
            "clock": ModuleClock(transpiler),
        }
        transpiler.modules = {**transpiler.modules, **modules}
        if import_thymio:
            transpiler.set_preamble("""from thymio import *
""")
        transpiler.set_source(src)
        transpiler.transpile()
        if warning_missing_global:
            w = missing_global_decl(transpiler)
            for function_name in w:
                for var_name in w[function_name]:
                    print(f"Warning: in function '{function_name}', '{var_name}' hides global variable.",
                          file=sys.stderr)
        return transpiler

    def clear_event_data(self, event_name=None, node=None):
        node_id = (self.node if node is None else node).id_str
        if node_id in self.event_data_dict:
            if event_name is None:
                del self.event_data_dict[node_id]
            elif event_name in self.event_data_dict[node_id]:
                del self.event_data_dict[node_id][event_name]

    def get_event_data(self, event_name=None, node=None):
        node_id = (self.node if node is None else node).id_str
        if node_id in self.event_data_dict:
            if event_name is None:
                return self.event_data_dict[node_id]
            else:
                return self.event_data_dict[node_id][event_name] if event_name in self.event_data_dict[node_id] else []
        else:
            return {} if event_name is None else []

    def reset_sync_var(self):
        self.sync_var = self.sync_var_vm.copy()
        # also pick user variables not known at connection time
        for name in self.node.var:
            self.sync_var.add(name)

    def process_events(self, on_event_data=None, all_nodes=False):
        """Listen to events sent by the program running on the robot and process
        them until _exit is received.

        Argument:
            on_event_data -- func(node, event_name) called when new data is received
        """

        exit_received = None  # or exit code once received

        def on_event_received(node, event_name, event_data):
            if self.output_enabled:
                if event_name == "_exit":
                    nonlocal exit_received
                    exit_received = event_data[0]
                elif event_name == "_print":
                    print_id = event_data[0]
                    print_format, print_num_args = print_statements[print_id]
                    print_args = tuple(event_data[1 : 1 + print_num_args])
                    print_str = print_format % print_args
                    print(print_str)
                else:
                    if len(event_data) > 0:
                        if node.id_str not in self.event_data_dict:
                            self.event_data_dict[node.id_str] = {}
                        if event_name not in self.event_data_dict[node.id_str]:
                            self.event_data_dict[node.id_str][event_name] = []
                        self.event_data_dict[node.id_str][event_name].append(event_data)
                        if on_event_data is not None:
                            on_event_data(node, event_name)

        def wake():
            return exit_received is not None

        self.client.clear_event_received_listeners()
        self.client.add_event_received_listener(on_event_received)
        try:
            if all_nodes:
                for node in self.client.nodes:
                    ClientAsync.aw(node.watch(events=True))
            else:
                ClientAsync.aw(self.node.watch(events=True))
            ClientAsync.aw(self.client.sleep(wake=wake))
            self.stop_program(self.node, discard_output=True)
            if exit_received:
                print(f"Exit, status={exit_received}")
        finally:
            if all_nodes:
                for node in self.client.nodes:
                    ClientAsync.aw(node.watch(events=False))
            else:
                ClientAsync.aw(self.node.watch(events=False))
            self.client.clear_event_received_listeners()

    def find_robot(self,
                  robot_id=None, robot_name=None,
                  robot_index=None):
        """Find the node specified by id, name or index.
        """
        if robot_index is not None:
            return self.client.nodes[robot_index]
        elif robot_id is not None or robot_name is not None:
            return self.client.first_node(node_id=robot_id,
                                          node_name=robot_name)

    def lock_robots(self, nodes):
        """Target the robot referenced by the key arguments, lock them if
        they aren't the default node, and return them; must be used with "with".
        """

        class Robot:
            """Utility class to be used with "with", to lock the nodes which
            aren't the default one and return them.
            """

            def __init__(self,
                         console,
                         default_node,
                         nodes):
                self.default_node = default_node
                self.nodes = nodes
                for node in nodes:
                    if node != default_node:
                        ClientAsync.aw(node.lock())

            def __enter__(self):
                return self.nodes

            def __exit__(self, type, value, traceback):
                for node in nodes:
                    if node != self.default_node:
                        node.unlock()

        return Robot(self, self.node, nodes)


    def run_program(self, src,
                    nodes=None,
                    language="aseba",
                    warning_missing_global=False,
                    wait=False,
                    import_thymio=True):
        if nodes is None:
            nodes = [self.node]

        running_nodes = set()

        # exit_received[node] = exit code once received
        exit_received = {}
        # print_statements[node][print_id] = (print_format, print_num_args)
        print_statements = {}

        def on_event_received(node, event_name, event_data):
            if self.output_enabled:
                if event_name == "_exit":
                    exit_received[node] = event_data[0]
                    if event_data[0]:
                        exit_str = f"Exit, status={event_data[0]}"
                        if len(nodes) > 1:
                            # multiple nodes: add prefix
                            exit_str = f"[R{nodes.index(node)}] " + exit_str
                        print(exit_str)
                    self.stop_program(node, discard_output=True)
                    running_nodes.remove(node)
                elif event_name == "_print":
                    print_id = event_data[0]
                    print_format, print_num_args = print_statements[node][print_id]
                    print_args = tuple(event_data[1 : 1 + print_num_args])
                    print_str = print_format % print_args
                    if len(nodes) > 1:
                        # multiple nodes: add prefix
                        print_str = f"[R{nodes.index(node)}] " + print_str
                    print(print_str)
                else:
                    if len(event_data) > 0:
                        if node.id_str not in self.event_data_dict:
                            self.event_data_dict[node.id_str] = {}
                        if event_name not in self.event_data_dict[node.id_str]:
                            self.event_data_dict[node.id_str][event_name] = []
                        self.event_data_dict[node.id_str][event_name].append(event_data)

        def on_vm_state_changed(node, state, line, error, error_msg):
            if error != ClientAsync.ERROR_NO_ERROR:
                exit_received[node] = f"vm error {error}"
            if error_msg:
                print(f"{error_msg} (line {line}{' in Aseba' if language != 'aseba' else ''})")

        def run_node(node):
            """Compile, configure node, load and start program on a node.
            Return True if the node requires waiting.
            """
            print_statements[node] = []
            events = []
            if language == "python":
                # transpile from Python to Aseba
                transpiler = self.transpile(src,
                                            import_thymio=import_thymio,
                                            warning_missing_global=warning_missing_global)
                src_aseba = transpiler.get_output()
                print_statements[node] = transpiler.print_format_strings
                if len(print_statements[node]) > 0:
                    events.append(("_print", 1 + transpiler.print_max_num_args))
                if transpiler.has_exit_event:
                    events.append(("_exit", 1))
                for event_name in transpiler.events_in:
                    events.append((event_name, transpiler.events_in[event_name]))
                for event_name in transpiler.events_out:
                    events.append((event_name, transpiler.events_out[event_name]))
                if len(events) > 0:
                    events = ClientAsync.aw(node.filter_out_vm_events(events))
                if len(events) > 0:
                    ClientAsync.aw(node.register_events(events))
            elif language == "aseba":
                src_aseba = src
            else:
                raise Exception(f"Unsupported language {language}")
            error = ClientAsync.aw(node.compile(src_aseba))
            if error is not None:
                raise Exception(error["error_msg"])
            node.send_set_scratchpad(src_aseba)
            wait_for_node = wait
            if wait is None:
                # default: wait if there are events to receive
                wait_for_node = len(events) > 0
            if wait_for_node:
                ClientAsync.aw(node.watch(events=True, vm_state=True))
            error = ClientAsync.aw(node.run())
            if error is not None:
                raise Exception(f"Error {error['error_code']}")
            return wait_for_node

        self.reset_sync_var()
        self.client.clear_event_received_listeners()
        self.client.add_event_received_listener(on_event_received)
        self.client.add_vm_state_changed_listener(on_vm_state_changed)
        wait_for_nodes = False
        with self.lock_robots(nodes) as nodes_l:
            # transpile, compile, load, set scratchpad, and run
            for node in nodes_l:
                wait_for_node = run_node(node)
                wait_for_nodes = wait_for_nodes or wait_for_node
                running_nodes.add(node)

        # wait until all nodes have exited
        if wait_for_nodes:
            try:
                def wake():
                    # True when all nodes have exited
                    return len(exit_received) >= len(nodes)
                ClientAsync.aw(self.client.sleep(wake=wake))
            finally:
                # stop nodes still running
                for node in running_nodes:
                    self.stop_program(node, discard_output=True)
                self.client.clear_event_received_listeners()
                self.client.clear_vm_state_changed_listener()

    def stop_program(self, node, discard_output=False):
        with self.lock_robots({node}) as nodes_l:
            output_enabled_orig = self.output_enabled
            self.output_enabled = not discard_output
            try:
                error = ClientAsync.aw(node.stop())
                if error is not None:
                    raise Exception(f"Error {error['error_code']}")
            finally:
                self.output_enabled = output_enabled_orig

    def from_python_name(self, name_py):
        # replace underscores with dots, except first underscore, for node variables
        if self.node is not None:
            name_a = re.sub(r"(?<=.)_", r".", name_py)
            if name_a in self.node.var:
                return name_a
        # not a node variable: keep as is
        return name_py

    @staticmethod
    def to_python_name(name_a):
        # replace dots with underscores
        return name_a.replace(".", "_")

    def fetch_variable(self, name_py, node_flush=True):
        """Fetch a variable from the robot and return its value.
        """

        if node_flush:
            self.node.flush()
        value = self.node[self.from_python_name(name_py)]
        if isinstance(value, ArrayCache):
            value = list(value)
        return value

    def fetch_variables(self, names_py, node_flush=True):
        """Fetch variables from the robot and store their values into
        self.local_var.
        """

        if node_flush:
            self.node.flush()
        for name_py in names_py:
            self.local_var[name_py] = self.fetch_variable(name_py,
                                                          node_flush=False)

    def send_variable(self, name_py, value):
        name_a = self.from_python_name(name_py)
        self.robot_var_set.add(name_a)
        self.node[name_a] = value

    def flush_variables(self):
        self.node.flush()

    def send_variables(self, names_py, node_flush=True):
        if len(names_py) > 0:
            for name_py in names_py:
                self.send_variable(name_py, self.local_var[name_py])
            if node_flush:
                self.flush_variables()

    def find_global_var(self, nodes, globals=None):
        """Return variable referenced in expressions, variables assigned to,
        variables declared as global, and function called (tuple of 4 sets).
        """

        if globals is None:
            globals = self.sync_var.copy()
        var_got = set()
        var_set = set()
        var_global = set()
        fun_called = set()

        def do_node(node):
            nonlocal globals, var_got, var_set, var_global

            # alternative to direct use of isinstance for node types
            # which aren't defined in Python 3.6
            def isinst(obj, ast_name):
                return (hasattr(ast, ast_name)
                        and isinstance(obj, getattr(ast, ast_name)))

            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            do_target(elt)
                    else:
                        do_target(target)
                do_node(node.value)
            elif isinstance(node, ast.AugAssign):
                do_target(node.target)
                do_node(node.value)
            elif isinstance(node, ast.Await):
                do_node(node.value)
            elif isinstance(node, ast.BinOp):
                do_node(node.left)
                do_node(node.right)
            elif isinstance(node, ast.BoolOp):
                do_nodes(node.values)
            elif isinstance(node, ast.Call):
                do_node(node.func)
                do_nodes(node.args)
                if isinstance(node.func, ast.Name):
                    fun_name = node.func.id
                    if (fun_name not in ATranspiler.PREDEFINED_FUNCTIONS
                        or fun_name in self.fun_defs):
                        fun_called.add(fun_name)
                    if fun_name in self.fun_defs:
                        # call to a user-defined function
                        var_got |= self.fun_defs[fun_name]["in"]
                        var_set |= self.fun_defs[fun_name]["out"]
            elif isinstance(node, ast.Compare):
                do_node(node.left)
                do_nodes(node.comparators)
            elif isinstance(node, ast.comprehension):
                do_target(node.target)
                do_nodes(node.iter)
                do_nodes(node.ifs)
            elif isinstance(node, ast.Dict):
                do_nodes(node.keys)
                do_nodes(node.values)
            elif isinstance(node, ast.DictComp):
                do_node(node.key)
                do_node(node.value)
                do_nodes(node.generators)
            elif isinstance(node, ast.ExceptHandler):
                do_nodes(node.body)
            elif isinstance(node, ast.Expr):
                do_node(node.value)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                do_target(node.target)
                do_node(node.iter)
                do_nodes(node.body)
                do_nodes(node.orelse)
            elif isinstance(node, ast.FormattedValue):
                do_node(node.value)
            elif isinstance(node, ast.GeneratorExp):
                do_node(node.elt)
                do_nodes(node.generators)
            elif isinstance(node, ast.Global):
                global_names = {
                    name
                    for name in node.names
                }
                globals |= global_names
                var_global |= global_names
            elif isinstance(node, ast.If):
                do_node(node.test)
                do_nodes(node.body)
                do_nodes(node.orelse)
            elif isinstance(node, ast.IfExp):
                do_node(node.test)
                do_node(node.body)
                do_node(node.orelse)
            elif isinstance(node, ast.Index):
                do_node(node.value)
            elif isinstance(node, ast.JoinedStr):
                do_nodes(node.values)
            elif isinstance(node, ast.Lambda):
                do_node(node.body)
            elif isinstance(node, ast.List):
                do_nodes(node.elts)
            elif isinstance(node, ast.ListComp):
                do_node(node.elt)
                do_nodes(node.generators)
            elif isinst(node, "Match"):
                do_node(node.subject)
                for c in node.cases:
                    do_node(c.pattern)
                    do_node(c.guard)
                    do_nodes(c.body)
            elif isinst(node, "MatchValue"):
                do_node(node.value)
            elif isinstance(node, ast.Name):
                if node.id in globals:
                    var_got.add(node.id)
            elif isinstance(node, ast.Return):
                do_node(node.value)
            elif isinstance(node, ast.Set):
                do_nodes(node.elts)
            elif isinstance(node, ast.SetComp):
                do_node(node.elt)
                do_nodes(node.generators)
            elif isinstance(node, ast.Slice):
                do_node(node.lower)
                do_node(node.upper)
                do_node(node.step)
            elif isinstance(node, ast.Starred):
                do_node(node.value)
            elif isinstance(node, ast.Subscript):
                do_node(node.value)
                do_node(node.slice)
            elif isinstance(node, ast.Try):
                do_nodes(node.body)
                do_nodes(node.handlers)
                do_nodes(node.orelse)
                do_nodes(node.finalbody)
            elif isinstance(node, ast.Tuple):
                do_nodes(node.elts)
            elif isinstance(node, ast.UnaryOp):
                do_node(node.operand)
            elif isinstance(node, ast.While):
                do_node(node.test)
                do_nodes(node.body)
                do_nodes(node.orelse)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    do_node(item.context_expr)
                do_nodes(node.body)
            elif isinstance(node, ast.Yield):
                do_node(node.value)
            elif isinstance(node, ast.YieldFrom):
                do_node(node.value)
            elif isinstance(node,
                            (ast.AsyncFunctionDef, ast.Attribute,
                             ast.Break,
                             ast.ClassDef, ast.Constant, ast.Continue,
                             ast.Delete,
                             ast.FunctionDef,
                             ast.Import, ast.ImportFrom,
                             ast.NameConstant, ast.Nonlocal, ast.Num,
                             ast.Pass,
                             ast.Str)):
                pass
            elif node is not None:
                print("Unchecked", ast.dump(node))

        def do_nodes(nodes):
            for node in nodes:
                do_node(node)

        def do_target(target):
            nonlocal globals

            if isinstance(target, ast.Name):
                if target.id in globals:
                    var_set.add(target.id)
            elif isinstance(target, ast.Subscript):
                if target.value.id in globals:
                    var_set.add(target.value.id)
                do_node(target.slice)

        do_nodes(nodes)
        return var_got, var_set, var_global, fun_called

    def pre_run(self, src):
        """Should be called before attempting to execute a partial or complete
        command.
        """
        self.var_got = set()
        self.var_set = set()
        self.cmd_src = src
        self.cmd_tree = None
        try:
            self.cmd_tree = ast.parse(src)
            self.var_got, self.var_set, _, _ = self.find_global_var(self.cmd_tree.body)
            self.var_got &= self.sync_var
            self.var_set &= self.sync_var
            self.fetch_variables(self.var_got)
        except Exception as e:
            # print("pre_run error", e)
            pass

    def get_function_def_src(self, node, next_node):
        # use bytes b/c col_offset is in bytes
        src_b = bytes(self.cmd_src, "utf-8")

        def index(lineno, col_offset):
            i = 0
            for _ in range(1, lineno):
                # start of next line
                i = src_b.index(b"\n", i) + 1
            return i + col_offset

        index_from = index(node.lineno, node.col_offset)
        if isinstance(node, ast.FunctionDef) and len(node.decorator_list) > 0:
            # special case for function decorators: include them
            for decorator in node.decorator_list:
                index_from = min(index_from,
                                 index(decorator.lineno, decorator.col_offset))
            # as well as first "@"
            while index_from > 0 and src_b[index_from - 1] in b" \t":
                index_from -= 1
            if src_b[index_from - 1] == ord("@"):
                index_from -= 1

        index_to = (index(next_node.lineno, next_node.col_offset)
                    if next_node is not None
                    else len(src_b))

        return str(src_b[index_from : index_to], "utf-8") + "\n"

    def post_run(self):
        """Analyze a complete command after it has been executed,
        with or without error.
        """
        self.send_variables(self.var_set)
        try:
            if (self.cmd_tree is not None and
                self.cmd_tree.body is not None):
                for i, statement in enumerate(self.cmd_tree.body):
                    if isinstance(statement, ast.FunctionDef):
                        # keep function source code
                        var_got, var_set, var_gl, fun_called = self.find_global_var(statement.body,
                                                                                    globals=set())
                        self.fun_defs[statement.name] = {
                            "src": self.get_function_def_src(statement,
                                                             self.cmd_tree.body[i + 1]
                                                             if i + 1 < len(self.cmd_tree.body)
                                                             else None),
                            "in": var_got,
                            "out": var_set,
                            "global": var_gl,
                            "calls": fun_called,
                        }
                    elif isinstance(statement, ast.Delete):
                        # discard function source code
                        for target in statement.targets:
                            if isinstance(target, ast.Name) and target.id in self.fun_defs:
                                del self.fun_defs[target.id]
                            if target.id in self.onevent_functions:
                                self.onevent_functions.remove(target.id)
        except Exception as e:
            pass

    def push(self, line):
        src = "\n".join([*self.buffer, line])
        self.pre_run(src)
        if len(line) > 0:
            r = super().push(line)  # True if incomplete
        else:
            # empty line
            # like InteractiveInterpreter.runsource, assuming src is complete
            try:
                self.resetbuffer()
                code = self.compile(src, "<stdin>", "single")
                if code is None:
                    raise SyntaxError("Incomplete code", ("<stdin>", 1, 0, src))
            except (OverflowError, SyntaxError, ValueError):
                self.showsyntaxerror("<stdin>")
                code = None
            if code is not None:
                self.runcode(code)
            r = False  # executed or error
        if not r:
            # executed
            self.post_run()
        return r

    def interact(self):
        banner = f"""TDM:      {self.client.tdm_addr}:{self.client.tdm_port}
Robot:    {self.node.props["name"]}
Robot ID: {self.node.props["node_id_str"]}
"""
        super().interact(banner=banner, exitmsg="")
