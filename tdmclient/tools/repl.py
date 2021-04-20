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
import getopt

from tdmclient import ClientAsync, ArrayCache
from tdmclient.atranspiler import ATranspiler

try:
    # line edition and history if available
    import readline
    # name completion if available
    import rlcompleter
    readline.parse_and_bind('tab:complete')
except ModuleNotFoundError:
    pass


class TDMConsole(code.InteractiveConsole):

    def __init__(self, fetch_variable=None, send_variable=None, flush_variables=None, functions=None, sync_var=None):
        self.local_var = {}
        if functions is not None:
            self.local_var = {**self.local_var, **functions}
        super().__init__(locals=self.local_var)
        self.fetch_variable = fetch_variable
        self.send_variable = send_variable
        self.flush_variables = flush_variables
        self.functions = {}
        self.sync_var = sync_var

        # for generating source code for robot
        self.robot_var_set = set()
        self.onevent_functions = set()

        # for current command
        self.var_got = set()
        self.var_set = set()

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
                    if fun_name in self.functions:
                        # call to a user-defined function
                        var_got |= self.functions[fun_name]["in"]
                        var_set |= self.functions[fun_name]["out"]
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

    def push(self, line):
        src = "\n".join([*self.buffer, line])
        tree = None
        self.var_got = set()
        self.var_set = set()
        try:
            tree = ast.parse(src)
            self.var_got, self.var_set, _ = self.find_global_var(tree.body)
            self.var_got &= self.sync_var
            self.var_set &= self.sync_var
            if self.fetch_variable is not None:
                for name in self.var_got:
                    self.local_var[name] = self.fetch_variable(name)
        except Exception as e:
            # print("ast.parse error", e)
            pass
        if len(line) > 0:
            r = super().push(line)
        else:
            # empty line
            # like InteractiveInterpreter.runsource, forcing src is complete
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
            r = False
        if not r:
            # executed
            if len(self.var_set) > 0:
                if self.send_variable is not None:
                    for name in self.var_set:
                        self.send_variable(name, self.local_var[name])
                if self.flush_variables is not None:
                    self.flush_variables()
            try:
                if (tree is not None and
                    tree.body is not None and
                    len(tree.body) > 0):
                    if isinstance(tree.body[0], ast.FunctionDef):
                        # keep function source code
                        var_got, var_set, fun_called = self.find_global_var(tree.body[0].body,
                                                                            globals=set())
                        self.functions[tree.body[0].name] = {
                            "src": src,
                            "in": var_got,
                            "out": var_set,
                            "calls": fun_called,
                        }
                    elif isinstance(tree.body[0], ast.Delete):
                        # discard function source code
                        for target in tree.body[0].targets:
                            if isinstance(target, ast.Name) and target.id in self.functions:
                                del self.functions[target.id]
                            if target.id in self.onevent_functions:
                                self.onevent_functions.remove(target.id)
            except Exception as e:
                print(e)
                pass
        return r

    def interact(self, banner="TDM Console"):
        super().interact(banner=banner, exitmsg="")


def help():
    print("""Usage: python3 -m tdmclient.tools.repl [options]
Read-eval-print loop with link and synchronization with Thymio

Options:
  --help       display this help message and exit
  --tdmaddr=H  tdm address (default: localhost or from zeroconf)
  --tdmport=P  tdm port (default: from zeroconf)
""")


if __name__ == "__main__":

    tdm_addr = None
    tdm_port = None

    try:
        arguments, values = getopt.getopt(sys.argv[1:],
                                          "",
                                          [
                                              "help",
                                              "tdmaddr=",
                                              "tdmport=",
                                          ])
    except getopt.error as err:
        print(str(err))
        sys.exit(1)
    for arg, val in arguments:
        if arg == "--help":
            help()
            sys.exit(0)
        elif arg == "--tdmaddr":
            tdm_addr = val
        elif arg == "--tdmport":
            tdm_port = int(val)

    with ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port) as client:

        async def co_init():
            with await client.lock() as node:
                await node.watch(variables=True)
                banner = f"""TDM:      {client.tdm_addr}:{client.tdm_port}
Robot:    {node.props["name"]}
Robot ID: {node.props["node_id_str"]}
"""

                interactive_console = None

                def from_python_name(p_name):
                    # replace underscores with dots, except first underscore
                    return re.sub(r"(?<=.)_", r".", p_name)

                def to_python_name(a_name):
                    # replace dots with underscores
                    return a_name.replace(".", "_")

                def fetch_variable(name):
                    node.flush()
                    value = node[from_python_name(name)]
                    if isinstance(value, ArrayCache):
                        value = list(value)
                    return value

                def send_variable(name, value):
                    a_name = from_python_name(name)
                    interactive_console.robot_var_set.add(a_name)
                    node[a_name] = value

                def flush_variables():
                    node.flush()

                def onevent(fun):
                    # function decorator @onevent
                    interactive_console.onevent_functions.add(fun.__name__)
                    return fun

                def sleep(t):
                    # send and flush all variables which might have been changed
                    if len(interactive_console.var_set) > 0:
                        for name in interactive_console.var_set:
                            send_variable(name, interactive_console.local_var[name])
                        flush_variables()

                    # wait
                    ClientAsync.aw(client.sleep(t))

                    # fetch all variables which might be used
                    for name in interactive_console.var_got:
                        interactive_console.local_var[name] = fetch_variable(name)

                def robot_code():
                    # gather source code for Thymio
                    src = ""

                    # robot variables
                    for name in interactive_console.robot_var_set:
                        src += f"""{to_python_name(name)} = {fetch_variable(name)}
"""

                    # onevent
                    functions_called = set()
                    for name in interactive_console.onevent_functions:
                        src += interactive_console.functions[name]["src"]
                        functions_called |= interactive_console.functions[name]["calls"]

                    # functions called from onevent
                    functions_added = interactive_console.onevent_functions
                    while True:
                        functions_remaining = functions_called.difference(functions_added)
                        if len(functions_remaining) == 0:
                            break
                        name = list(functions_remaining)[0]
                        src += interactive_console.functions[name]["src"]
                        functions_added.add(name)
                        functions_called |= interactive_console.functions[name]["calls"]

                    return src

                def run():
                    # gather Python source code for Thymio
                    src_py = robot_code()
                    # transpile from Python to Aseba
                    src_a = ATranspiler.simple_transpile(src_py)
                    # compile, load and run
                    error = ClientAsync.aw(node.compile(src_a))
                    if error is not None:
                        raise Exception(error["error_msg"])
                    error = ClientAsync.aw(node.run())
                    if error is not None:
                        raise Exception(f"Error {error['error_code']}")

                def stop():
                    error = ClientAsync.aw(node.stop())
                    if error is not None:
                        raise Exception(f"Error {error['error_code']}")

                interactive_console = TDMConsole(
                    fetch_variable=fetch_variable,
                    send_variable=send_variable,
                    flush_variables=flush_variables,
                    functions={
                        "onevent": onevent,
                        "sleep": sleep,
                        "robot_code": robot_code,
                        "run": run,
                        "stop": stop,
                    }
                )

                # fetch all variables
                await node.wait_for_variables()
                sync_var = set()
                for name in node.vm_description["variables"]:
                    value = node[name]
                    if isinstance(value, ArrayCache):
                        value = list(value)
                    name_py = to_python_name(name)
                    interactive_console.local_var[name_py] = value
                    sync_var.add(name_py)
                interactive_console.sync_var = sync_var

                interactive_console.interact(banner)

        client.run_async_program(co_init)
