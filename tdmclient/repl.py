# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import code
import ast
import sys
import re

from tdmclient import ClientAsync, ArrayCache
from tdmclient.atranspiler import ATranspiler
from tdmclient.module_thymio import ModuleThymio


class TDMConsole(code.InteractiveConsole):

    def __init__(self, local_var=None, define_functions=True):
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
            if len(self.var_set) > 0:
                for name in self.var_set:
                    self.send_variable(name, self.local_var[name])
                self.flush_variables()

            # wait
            ClientAsync.aw(self.client.sleep(t))

            # fetch all variables which might be used
            for name in self.var_got:
                self.local_var[name] = self.fetch_variable(name)

        def robot_code(language="python"):
            """Gather Python or Aseba source code for the robot.

            Argument:
                language -- "python" (default) or "aseba"
            """

            src = ""

            # robot variables
            for name in self.robot_var_set:
                name_py = self.to_python_name(name)
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

        def run(wait=None):
            """Run program obtained by robot_code on the robot. By default, wait
            to process events until "_exit" is received (call to "exit()" in the
            robot's program), or return immediately if the program doesn't send
            any event.
            """
            src_p = robot_code()
            # compile, load, run, and set scratchpad without checking the result
            self.run_program(src_p, language="python", wait=wait)

        def stop():
            """Stop the program running on the robot.
            """
            self.stop_program(discard_output=True)

        def clear_event_data(event_name=None):
            """Clear all or named event data.
            """
            self.clear_event_data(event_name)

        def get_event_data(event_name=None):
            """Get list of event data received until now.
            """
            return self.get_event_data(event_name)

        self.functions = {
            "onevent": onevent,
            "sleep": sleep,
            "robot_code": robot_code,
            "robot_code_new": robot_code_new,
            "run": run,
            "stop": stop,
            "clear_event_data": clear_event_data,
            "get_event_data": get_event_data,
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
        for name in self.node.vm_description["variables"]:
            value = self.node[name]
            if isinstance(value, ArrayCache):
                value = list(value)
            name_py = self.to_python_name(name)
            self.local_var[name_py] = value
            sync_var.add(name_py)
        self.sync_var = sync_var

    @staticmethod
    def transpile(src, import_thymio=True):
        """Transpile Python source code to Aseba and returns transpiler.

        Argument:
            src -- Python source code
            import_thymio -- if True (default), predefine all Thymio symbols
        """
        modules = {
            "thymio": ModuleThymio()
        }
        transpiler = ATranspiler()
        transpiler.modules = {**transpiler.modules, **modules}
        if import_thymio:
            transpiler.set_preamble("""from thymio import *
""")
        transpiler.set_source(src)
        transpiler.transpile()
        return transpiler

    def clear_event_data(self, event_name=None):
        if event_name is None:
            self.event_data_dict = {}
        elif event_name in self.event_data_dict:
            del self.event_data_dict[event_name]

    def get_event_data(self, event_name=None):
        if event_name is None:
            return self.event_data_dict
        else:
            return self.event_data_dict[event_name] if event_name in self.event_data_dict else []

    def run_program(self, src, language="aseba", wait=False, import_thymio=True):
        print_statements = []
        events = []
        if language == "python":
            # transpile from Python to Aseba
            transpiler = self.transpile(src, import_thymio)
            src = transpiler.get_output()
            print_statements = transpiler.print_format_strings
            if len(print_statements) > 0:
                events.append(("_print", 1 + transpiler.print_max_num_args))
            if transpiler.has_exit_event:
                events.append(("_exit", 1))
            for event_name in transpiler.events:
                events.append((event_name, transpiler.events[event_name]))
            if len(events) > 0:
                ClientAsync.aw(self.node.register_events(events))
        elif language != "aseba":
            raise Exception(f"Unsupported language {language}")
        # compile, load, run, and set scratchpad without checking the result
        error = ClientAsync.aw(self.node.compile(src))
        if error is not None:
            raise Exception(error["error_msg"])
        exit_received = None  # or exit code once received
        if wait is None:
            # wait if there are events to receive
            wait = len(events) > 0
        if len(events) > 0 and wait:
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
                            if event_name not in self.event_data_dict:
                                self.event_data_dict[event_name] = []
                            self.event_data_dict[event_name].append(event_data)
            self.client.clear_event_received_listeners()
            self.client.add_event_received_listener(on_event_received)
            ClientAsync.aw(self.node.watch(events=True))
        error = ClientAsync.aw(self.node.run())
        if error is not None:
            raise Exception(f"Error {error['error_code']}")
        self.node.send_set_scratchpad(src)
        if wait:
            def wake():
                return exit_received is not None
            ClientAsync.aw(self.client.sleep(wake=wake))
            self.stop_program(discard_output=True)
            if exit_received:
                print(f"Exit, status={exit_received}")

    def stop_program(self, discard_output=False):
        output_enabled_orig = self.output_enabled
        self.output_enabled = not discard_output
        try:
            error = ClientAsync.aw(self.node.stop())
            if error is not None:
                raise Exception(f"Error {error['error_code']}")
        finally:
            self.output_enabled = output_enabled_orig

    @staticmethod
    def from_python_name(p_name):
        # replace underscores with dots, except first underscore
        return re.sub(r"(?<=.)_", r".", p_name)

    @staticmethod
    def to_python_name(a_name):
        # replace dots with underscores
        return a_name.replace(".", "_")

    def fetch_variable(self, name):
        self.node.flush()
        value = self.node[self.from_python_name(name)]
        if isinstance(value, ArrayCache):
            value = list(value)
        return value

    def send_variable(self, name, value):
        a_name = self.from_python_name(name)
        self.robot_var_set.add(a_name)
        self.node[a_name] = value

    def flush_variables(self):
        self.node.flush()

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
                do_nodes(node.args)
                ast.dump(node)
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
            elif isinstance(node, ast.List):
                do_nodes(node.elts)
            elif isinstance(node, ast.ListComp):
                do_node(node.elt)
                do_nodes(node.generators)
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
                             ast.Delete, ast.FunctionDef,
                             ast.Import, ast.ImportFrom,
                             ast.Lambda,
                             ast.Nonlocal,
                             ast.Pass)):
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
            for name in self.var_got:
                self.local_var[name] = self.fetch_variable(name)
        except Exception as e:
            # print("pre_run error", e)
            pass

    def get_function_def_src(self, node):
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
            else:
                raise SyntaxError("Internal error",
                                  ("<stdin>",
                                   node.decorator_list[0].lineno,
                                   node.decorator_list[0].col_offset,
                                   self.cmd_src))

        index_to = index(node.end_lineno, node.end_col_offset)

        return str(src_b[index_from : index_to], "utf-8") + "\n"

    def post_run(self):
        """Analyze a complete command after it has been executed,
        with or without error.
        """
        if len(self.var_set) > 0:
            for name in self.var_set:
                self.send_variable(name, self.local_var[name])
            self.flush_variables()
        try:
            if (self.cmd_tree is not None and
                self.cmd_tree.body is not None):
                for statement in self.cmd_tree.body:
                    if isinstance(statement, ast.FunctionDef):
                        # keep function source code
                        var_got, var_set, var_gl, fun_called = self.find_global_var(statement.body,
                                                                                    globals=set())
                        self.fun_defs[statement.name] = {
                            "src": self.get_function_def_src(statement),
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
