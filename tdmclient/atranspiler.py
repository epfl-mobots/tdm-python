# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Python-to-Aseba transpiler (actually a tiny, yet useful subset of Python)
"""

import sys
import ast


class ATranspiler:

    PREDEFINED_VARIABLES = {
        "acc": 3,
        "button.backward": None,
        "button.center": None,
        "button.forward": None,
        "button.left": None,
        "button.right": None,
        "events.arg": 32,
        "events.source": None,
        "leds.bottom.left": 3,
        "leds.bottom.right": 3,
        "leds.circle": 8,
        "leds.top": 3,
        "mic.intensity": None,
        "mic.threshold": None,
        "motor.left.pwm": None,
        "motor.left.speed": None,
        "motor.left.target": None,
        "motor.right.pwm": None,
        "motor.right.speed": None,
        "motor.right.target": None,
        "prox.comm.rx": None,
        "prox.comm.tx": None,
        "prox.ground.ambient": 2,
        "prox.ground.delta": 2,
        "prox.ground.reflected": 2,
        "prox.horizontal": 7,
        "rc5.address": None,
        "rc5.command": None,
        "sd.present": None,
        "temperature": None,
        "timer.period": 2,
    }

    def __init__(self):
        self.src = None
        self.ast = None
        self.output_src = None

    def set_source(self, source):
        self.src = source
        self.ast = None
        self.output_src = None

    def decode_attr(self, node):
        name = ""
        while isinstance(node, ast.Attribute):
            name = "." + node.attr + name
            node = node.value
        if isinstance(node, ast.Name):
            name = node.id + name
        else:
            raise Exception("Invalid name")
        return name

    def split(self):
        top_code = []
        functions = {}
        event_handlers = {}
        for node in self.ast.body:
            if isinstance(node, ast.FunctionDef):
                event_id = None
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Name):
                        raise Exception(f"Unsupported function decorator type {ast.dump(decorator)}")
                    if decorator.func.id != "onevent":
                        raise Exception(f'Unsupported function decorator "{decorator.func.id}"')
                    if len(decorator.args) != 1:
                        raise Exception("Unsupported function decorator number of arguments")
                    if (isinstance(decorator.args[0], ast.Num)):
                        event_id = decorator.args[0].n
                        if (event_id & 0xffff) == 0xffff:
                            # init event handler is made of top-level code,
                            # not a decorated function
                            raise Exception("Illegal event id 0xffff")
                    else:
                        raise Exception(f"Unsupported function decorator argument type {ast.dump(decorator.args[0])}")
                if event_id is None:
                    functions[node.name] = node
                else:
                    event_handlers[event_id] = node
            else:
                top_code.append(node)

        return top_code, functions, event_handlers

    # http://wiki.thymio.org/en:asebalanguage
    PRI_LOW = 0
    PRI_ASSGN = 1
    PRI_COMMA = 2
    PRI_LOGICAL_OR = 3
    PRI_LOGICAL_AND = 4
    PRI_LOGICAL_NOT = 5
    PRI_COMPARISON = 6
    PRI_BINARY_OR = 7
    PRI_BINARY_XOR = 8
    PRI_BINARY_AND = 9
    PRI_SHIFT = 10
    PRI_ADD = 11
    PRI_MOD = 12
    PRI_MULT = 13
    PRI_ABS = 14
    PRI_BINARY_NOT = 15
    PRI_UNARY_MINUS = 16

    def compile_expr(self, node, priority_container=PRI_LOW):
        if isinstance(node, ast.Num):
            return f"{node.n:d}"
        elif isinstance(node, ast.BinOp):
            op = node.op
            if isinstance(op, ast.Add):
                priority = self.PRI_ADD
                code = self.compile_expr(node.left, priority) + " + " + self.compile_expr(node.right, priority)
            elif isinstance(op, ast.FloorDiv):
                priority = self.PRI_MULT
                code = self.compile_expr(node.left, priority) + " / " + self.compile_expr(node.right, priority)
            elif isinstance(op, ast.LShift):
                priority = self.PRI_SHIFT
                code = self.compile_expr(node.left, priority) + " << " + self.compile_expr(node.right, priority)
            elif isinstance(op, ast.Mod):
                priority = self.PRI_MOD
                code = self.compile_expr(node.left, priority) + " % " + self.compile_expr(node.right, priority)
            elif isinstance(op, ast.Mult):
                priority = self.PRI_MULT
                code = self.compile_expr(node.left, priority) + " * " + self.compile_expr(node.right, priority)
            elif isinstance(op, ast.RShift):
                priority = self.PRI_SHIFT
                code = self.compile_expr(node.left, priority) + " >> " + self.compile_expr(node.right, priority)
            elif isinstance(op, ast.Sub):
                priority = self.PRI_ADD
                code = self.compile_expr(node.left, priority) + " - " + self.compile_expr(node.right, priority)
            else:
                raise Exception(f"Binary op {ast.dump(node.op)} not implemented")
            return code if priority >= priority_container else "(" + code + ")"
        elif isinstance(node, ast.Constant):
            if node.value is False:
                return "0"
            elif node.value is True:
                return "1"
            else:
                raise Exception(f"Unsupported constant {node.value}")
        elif isinstance(node, ast.List):
            if priority_container > self.PRI_ASSGN:
                raise Exception("List not supported in expression")
            code = "[" + ", ".join([
                                       self.compile_expr(el, self.PRI_COMMA)
                                       for el in node.elts
                                   ]) + "]"
            return code
        elif isinstance(node, ast.Name):
            return self.decode_attr(node)
        elif isinstance(node, ast.UnaryOp):
            op = node.op
            if isinstance(op, ast.UAdd):
                priority = self.PRI_ADD
                code = self.compile_expr(node.operand, priority)
            elif isinstance(op, ast.Invert):
                priority = self.PRI_BINARY_NOT
                code = "~" + self.compile_expr(node.operand, priority)
            elif isinstance(op, ast.Not):
                priority = self.PRI_UNARY_NOT
                code = "not " + self.compile_expr(node.operand, priority)
            elif isinstance(op, ast.USub):
                priority = self.PRI_UNARY_MINUS
                code = "-" + self.compile_expr(node.operand, priority)
            else:
                raise Exception(f"Unary op {ast.dump(node.op)} not implemented")
            return code if priority >= priority_container else "(" + code + ")"
        else:
            raise Exception(f"Node {ast.dump(node)} not implemented")

    def compile_node(self, node):
        code = ""
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise Exception(f"Unsupported assignment to {len(node.targets)} targets")
            target = self.decode_attr(node.targets[0])
            code = f"{target} = {self.compile_expr(node.value)}\n"
            target_size = len(node.value.elts) if isinstance(node.value, ast.List) else None
            return code, {target: target_size}
        else:
            raise Exception(f"Node {ast.dump(node)} not implemented")

    def compile_node_array(self, node_array):
        code = ""
        var = {}
        for node in node_array:
            c, v = self.compile_node(node)
            code += c
            for name in v:
                if (name in var and v[name] != var[name] or
                    name in self.PREDEFINED_VARIABLES and v[name] != self.PREDEFINED_VARIABLES[name]):
                    raise Exception(f"Incompatible sizes for list assignment to {name}")
                var = {**var, **v}
        return code, var

    def transpile(self):
        self.ast = ast.parse(self.src)
        top_code, functions, event_handlers = self.split()

        self.output_src = ""
        self.output_src, var = self.compile_node_array(top_code)
        if len(var) > 0:
            var_decl = "".join([
                f"var {v}{f'[{var[v]}]' if var[v] is not None else ''}\n"
                for v in var
                if v not in self.PREDEFINED_VARIABLES
            ])
            self.output_src = var_decl + "\n" + self.output_src

    def get_output(self):
        return self.output_src


if __name__ == "__main__":

    src = None

    if src is None:
        src = sys.stdin.read()

    transpiler = ATranspiler()
    transpiler.set_source(src)
    transpiler.transpile()
    output_src = transpiler.get_output()
    print(output_src)
