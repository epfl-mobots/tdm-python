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


class TDMConsole(code.InteractiveConsole):

    def __init__(self):
        # client and node set in async init
        self.client = None
        self.node = None

        def onevent(fun):
            # function decorator @onevent
            self.onevent_functions.add(fun.__name__)
            return fun

        def sleep(t):
            # send and flush all variables which might have been changed
            if len(self.var_set) > 0:
                for name in self.var_set:
                    send_variable(name, self.local_var[name])
                self.flush_variables()

            # wait
            ClientAsync.aw(self.client.sleep(t))

            # fetch all variables which might be used
            for name in self.var_got:
                self.local_var[name] = self.fetch_variable(name)

        def robot_code(language="python"):
            # gather Python or Aseba source code for Thymio
            src = ""

            # robot variables
            for name in self.robot_var_set:
                src += f"""{self.to_python_name(name)} = {self.fetch_variable(name)}
"""

            # onevent
            functions_called = set()
            for name in self.onevent_functions:
                src += self.fun_defs[name]["src"]
                functions_called |= self.fun_defs[name]["calls"]

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

            if language == "aseba":
                # transpile from Python to Aseba
                src = ATranspiler.simple_transpile(src)
            elif language != "python":
                raise Exception(f"Unsupported language {language}")

            return src

        def robot_code_new():
            # forget assignments and definitions used to generate robot code
            self.robot_var_set.clear()
            self.onevent_functions.clear()

        def run():
            # gather Aseba source code for Thymio
            src_a = robot_code(language="aseba")
            # compile, load and run
            error = ClientAsync.aw(self.node.compile(src_a))
            if error is not None:
                raise Exception(error["error_msg"])
            error = ClientAsync.aw(self.node.run())
            if error is not None:
                raise Exception(f"Error {error['error_code']}")

        def stop():
            error = ClientAsync.aw(self.node.stop())
            if error is not None:
                raise Exception(f"Error {error['error_code']}")

        self.functions = {
            "onevent": onevent,
            "sleep": sleep,
            "robot_code": robot_code,
            "robot_code_new": robot_code_new,
            "run": run,
            "stop": stop,
        }
        self.local_var = self.functions.copy()

        super().__init__(locals=self.local_var)

        self.sync_var = None

        # for generating source code for robot
        self.robot_var_set = set()
        self.fun_defs = {}
        self.onevent_functions = set()

        # for current command
        self.var_got = set()
        self.var_set = set()

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
        if globals is None:
            globals = self.sync_var.copy()
        var_got = set()
        var_set = set()
        fun_called = set()

        def do_node(node):
            nonlocal globals, var_got, var_set

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
            elif isinstance(node, ast.For):
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
                globals |= {
                    name
                    for name in node.names
                }
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
            elif isinstance(node, ast.Yield):
                do_node(node.value)
            elif isinstance(node, ast.YieldFrom):
                do_node(node.value)
            elif isinstance(node, (ast.AsyncFunctionDef, ast.Attribute, ast.ClassDef, ast.Constant, ast.Delete, ast.FunctionDef, ast.Import, ast.Pass)):
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
        return var_got, var_set, fun_called

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
            self.var_got, self.var_set, _ = self.find_global_var(self.cmd_tree.body)
            self.var_got &= self.sync_var
            self.var_set &= self.sync_var
            if self.fetch_variable is not None:
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
            if self.send_variable is not None:
                for name in self.var_set:
                    self.send_variable(name, self.local_var[name])
            self.flush_variables()
        try:
            if (self.cmd_tree is not None and
                self.cmd_tree.body is not None):
                for statement in self.cmd_tree.body:
                    if isinstance(statement, ast.FunctionDef):
                        # keep function source code
                        var_got, var_set, fun_called = self.find_global_var(statement.body,
                                                                            globals=set())
                        self.fun_defs[statement.name] = {
                            "src": self.get_function_def_src(statement),
                            "in": var_got,
                            "out": var_set,
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
