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
                event_name = None
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Name):
                        raise Exception(f"Unsupported function decorator type {ast.dump(decorator)}")
                    if decorator.id != "onevent":
                        raise Exception(f'Unsupported function decorator "{decorator.id}"')
                    event_name = node.name
                if event_name is None:
                    functions[node.name] = node
                elif event_name in event_handlers:
                    raise Exception(f"Onevent handler {event_name} defined multiple times")
                else:
                    event_handlers[event_name] = node
            else:
                top_code.append(node)

        return top_code, functions, event_handlers

    # http://wiki.thymio.org/en:asebalanguage
    PRI_LOW = 0
    PRI_ASSIGN = 1
    PRI_COMMA = 2
    PRI_LOGICAL_OR = 3
    PRI_LOGICAL_AND = 4
    PRI_LOGICAL_NOT = 5
    PRI_COMPARISON = 6
    PRI_NUMERIC = 7
    PRI_BINARY_OR = 8
    PRI_BINARY_XOR = 9
    PRI_BINARY_AND = 10
    PRI_SHIFT = 11
    PRI_ADD = 12
    PRI_MOD = 13
    PRI_MULT = 14
    PRI_ABS = 15
    PRI_BINARY_NOT = 16
    PRI_UNARY_MINUS = 17
    PRI_HIGH = 100

    def compile_expr(self, node, priority_container=PRI_LOW, tmp_offset=0):
        """Compile an expression or subexpression.
        Return the expression, additional statements to calculate auxiliary values,
        total requirements of temporary array tmp[], and whether result is boolean.
        """
        code = None
        aux_statements = ""
        tmp_req = tmp_offset
        priority = self.PRI_HIGH
        is_boolean = False

        if isinstance(node, ast.Num):
            code = f"{node.n:d}"
        elif isinstance(node, ast.BinOp):
            op = node.op
            op_str, priority = {
                ast.Add: ("+", self.PRI_ADD),
                ast.BitAnd: ("&", self.PRI_BINARY_AND),
                ast.BitOr: ("|", self.PRI_BINARY_OR),
                ast.BitXor: ("^", self.PRI_BINARY_XOR),
                ast.FloorDiv: ("/", self.PRI_MULT),
                ast.LShift: ("+¨<<", self.PRI_SHIFT),
                ast.Mod: ("%", self.PRI_MOD),
                ast.Mult: ("*", self.PRI_MULT),
                ast.RShift: (">>", self.PRI_SHIFT),
                ast.Sub: ("-", self.PRI_ADD),
            }[type(op)]
            left, aux_st, tmp_req, _ = self.compile_expr(node.left, priority, tmp_req)
            aux_statements += aux_st
            right, aux_st, tmp_req, _ = self.compile_expr(node.right, priority, tmp_req)
            aux_statements += aux_st
            code = f"{left} {op_str} {right}"
        elif isinstance(node, ast.BoolOp):
            # with shortcuts, useful e.g. to avoid out-of-bound array indexing
            # result is not pretty b/c of aseba's idea of what's acceptable
            op = node.op
            cmp = "!=" if isinstance(op, ast.And) else "=="
            tmp_offset = tmp_req
            tmp_req += 1
            for i in range(len(node.values)):
                value, aux_st, tmp_req1, is_value_boolean = self.compile_expr(node.values[i], self.PRI_ASSIGN, tmp_offset + 1)
                tmp_req = max(tmp_req, tmp_req1)
                # store value into tmp[tmp_offset]
                aux_statements += aux_st
                if is_value_boolean:
                    aux_statements += f"""if {value} then
\ttmp[{tmp_offset}] = 1
else
\ttmp[{tmp_offset}] = 0
end
"""
                else:
                    aux_statements += f"""tmp[{tmp_offset}] = {value}
"""
                # continue evaluating terms if true (and) or false (or)
                if i + 1 < len(node.values):
                    aux_statements += f"""if tmp[{tmp_offset}] {cmp} 0 then
"""
            for i in range(len(node.values) - 1):
                aux_statements += """end
"""
            code = f"tmp[{tmp_offset}]"
            is_boolean = False
        elif isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                raise Exception("Chained comparisons not implemented")
            op = node.ops[0]
            op_str = {
                ast.Eq: "==",
                ast.Gt: ">",
                ast.GtE: ">=",
                ast.Lt: "<",
                ast.LtE: "<=",
                ast.NotEq: "!=",
            }[type(op)]
            priority = self.PRI_COMPARISON
            left, aux_st, tmp_req, _ = self.compile_expr(node.left, self.PRI_NUMERIC, tmp_req)
            aux_statements += aux_st
            right, aux_st, tmp_req, _ = self.compile_expr(node.comparators[0], self.PRI_NUMERIC, tmp_req)
            aux_statements += aux_st
            if op_str is None:
                raise Exception(f"Comparison op {ast.dump(op)} not implemented")
            code = f"{left} {op_str} {right}"
            is_boolean = True
        elif isinstance(node, ast.Constant) or isinstance(node, ast.NameConstant):
            if node.value is False:
                code = "0"
            elif node.value is True:
                code = "1"
            else:
                raise Exception(f"Unsupported constant {node.value}")
        elif isinstance(node, ast.List):
            if priority_container > self.PRI_ASSIGN:
                raise Exception("List not supported in expression")
            for el in node.elts:
                el_code, aux_st, tmp_req, is_boolean = self.compile_expr(el, self.PRI_NUMERIC, tmp_req)
                aux_statements += aux_st
                if code is None:
                    code = "[" + el_code
                else:
                    code += ", " + el_code
            code += "]"
            return code, aux_statements, tmp_req, False
        elif isinstance(node, ast.Name):
            code = self.decode_attr(node)
        elif isinstance(node, ast.Subscript):
            name = self.decode_attr(node.value)
            index = node.slice.value
            index_value, aux_st, tmp_req, is_index_boolean = self.compile_expr(index, self.PRI_NUMERIC, tmp_req)
            if is_index_boolean:
                aux_st += f"""if {index_value} then
\ttmp[{tmp_req}] = 1
else
\ttmp[{tmp_req}] = 0
end
"""
                index_value = f"tmp[{tmp_req}]"
                tmp_req += 1
            aux_statements += aux_st
            code = f"{name}[{index_value}]"
        elif isinstance(node, ast.UnaryOp):
            op = node.op
            if isinstance(op, ast.UAdd):
                priority = self.PRI_ADD
                code, aux_st, tmp_req, is_boolean = self.compile_expr(node.operand, priority, tmp_req)
                aux_statements += aux_st
            elif isinstance(op, ast.Invert):
                priority = self.PRI_BINARY_NOT
                operand, aux_st, tmp_req, is_boolean = self.compile_expr(node.operand, priority, tmp_req)
                aux_statements += aux_st
                code = "~" + operand
            elif isinstance(op, ast.Not):
                priority = self.PRI_LOGICAL_NOT
                operand, aux_st, tmp_req, is_boolean = self.compile_expr(node.operand, priority, tmp_req)
                if is_boolean:
                    code = "not " + operand
                else:
                    code = operand + " == 0"
                    is_boolean = True
            elif isinstance(op, ast.USub):
                priority = self.PRI_UNARY_MINUS
                operand, aux_st, tmp_req, is_boolean = self.compile_expr(node.operand, priority, tmp_req)
                aux_statements += aux_st
                code = "-" + operand
            else:
                raise Exception(f"Unsupported unary op {op}")
        else:
            raise Exception(f"Node {ast.dump(node)} not implemented")

        if priority < self.PRI_NUMERIC and priority_container >= self.PRI_NUMERIC:
            # work around aseba's idea of what's acceptable
            # (no boolean in arithmetic subexpressions or variables)
            aux_statements += f"""if {code} then
\ttmp[{tmp_offset}] = 1
else
\ttmp[{tmp_offset}] = 0
end
"""
            tmp_req = max(tmp_req, tmp_offset + 1)
            return f"tmp[{tmp_offset}]", aux_statements, tmp_req, False
        elif priority < priority_container:
            return "(" + code + ")", aux_statements, tmp_req, is_boolean
        else:
            return code, aux_statements, tmp_req, is_boolean

    def decode_target(self, target):
        """Decode an assignment target and return variable name (possibly dotted) and
        index node (or None)
        """
        index = None
        if isinstance(target, ast.Subscript):
            index = target.slice.value
            target = target.value
        name = self.decode_attr(target)
        return name, index

    def compile_node(self, node, tmp_req=0):
        code = ""
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise Exception("Unsupported assignment to multiple targets")
            target, index = self.decode_target(node.targets[0])
            if isinstance(node.value, ast.List):
                if index is not None:
                    raise Exception("List assigned to indexed variable")
                value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.value, self.PRI_ASSIGN, tmp_req)
            else:
                value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.value, self.PRI_NUMERIC, tmp_req)
            code += aux_statements
            if index is not None:
                index_value, aux_statements, tmp_req, is_index_boolean = self.compile_expr(index, self.PRI_NUMERIC, tmp_req)
                code += aux_statements
                if is_index_boolean:
                    code += f"""if {index_value} then
\ttmp[{tmp_req}] = 1
else
\ttmp[{tmp_req}] = 0
end
"""
                    index_value = "tmp[{tmp_req}]"
                    tmp_req += 1
                target += "[" + index_value + "]"
            if is_boolean:
                # convert boolean to number
                code += f"""if {value} then
\t{target} = 1
else
\t{target} = 0
end
"""
                tmp_req = max(tmp_req, 1)
            else:
                code += f"{target} = {value}\n"
            target_size = len(node.value.elts) if isinstance(node.value, ast.List) else None
            return code, {target: target_size} if index is None else {}, tmp_req
        elif isinstance(node, ast.If):
            tmp_offset = tmp_req
            test_value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.test, self.PRI_LOW, tmp_req)
            code += aux_statements
            code += f"""if {test_value}{"" if is_boolean else " != 0"} then
"""
            body, var, tmp_req1 = self.compile_node_array(node.body, tmp_offset)
            code += body
            tmp_req = max(tmp_req, tmp_req1)
            while len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # "if" node as single element of orelse: elif
                node = node.orelse[0]
                test_value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.test, self.PRI_LOW, tmp_req)
                code += aux_statements
                code += f"""elseif {test_value}{"" if is_boolean else " != 0"} then
"""
                body, var, tmp_req1 = self.compile_node_array(node.body, tmp_offset)
                code += body
                tmp_req = max(tmp_req, tmp_req1)
            if len(node.orelse) > 0:
                # anything else in orelse: else
                code += f"""else
"""
                body, var, tmp_req1 = self.compile_node_array(node.orelse, tmp_offset)
                code += body
                tmp_req = max(tmp_req, tmp_req1)
            code += """end
"""
            return code, var, tmp_req
        elif isinstance(node, ast.Pass):
            return "", {}, tmp_req
        elif isinstance(node, ast.While):
            tmp_offset = tmp_req
            test_value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.test, self.PRI_LOW, tmp_req)
            code += aux_statements
            code += f"""while {test_value}{"" if is_boolean else " != 0"} do
"""
            body, var, tmp_req1 = self.compile_node_array(node.body, tmp_offset)
            code += body
            tmp_req = max(tmp_req, tmp_req1)
            code += aux_statements  # to evaluate condition
            code += """end
"""
            if node.orelse is not None and len(node.orelse) > 0:
                # else clause always executed b/c break is not supported
                body, var, tmp_req1 = self.compile_node_array(node.orelse, tmp_offset)
                code += body
                tmp_req = max(tmp_req, tmp_req1)
            return code, var, tmp_req
        else:
            raise Exception(f"Node {ast.dump(node)} not implemented")

    @staticmethod
    def check_var_size(var, var_new):
        for name in var_new:
            if (name in var and var_new[name] != var[name] or
                name in ATranspiler.PREDEFINED_VARIABLES and var_new[name] != ATranspiler.PREDEFINED_VARIABLES[name]):
                raise Exception(f"Incompatible sizes for list assignment to {name}")

    def compile_node_array(self, node_array, tmp_req=0):
        code = ""
        var = {}
        for node in node_array:
            c, v, tmp_req1 = self.compile_node(node, tmp_req)
            code += c
            self.check_var_size(var, v)
            var = {**var, **v}
            tmp_req = max(tmp_req, tmp_req1)
        return code, var, tmp_req

    def transpile(self):
        self.ast = ast.parse(self.src)
        top_code, functions, event_handlers = self.split()

        self.output_src = ""

        # top-level code
        self.output_src, var, tmp_req = self.compile_node_array(top_code)

        # onevent handlers
        tmp_offset = tmp_req
        for event_name in event_handlers:
            event_output_src, var1, tmp_req1 = self.compile_node_array(event_handlers[event_name].body, tmp_offset)
            tmp_req = max(tmp_req, tmp_req1)
            self.check_var_size(var, var1)
            var = {**var, **var1}
            self.output_src += f"""
onevent {event_name}
""" + event_output_src

        # variable declarations
        if tmp_req > 0:
            var["tmp"] = tmp_req
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
    if len(sys.argv) >= 2:
        with open(sys.argv[1]) as f:
            src = f.read()
    else:
        src = sys.stdin.read()

    transpiler = ATranspiler()
    transpiler.set_source(src)
    transpiler.transpile()
    output_src = transpiler.get_output()
    print(output_src)
