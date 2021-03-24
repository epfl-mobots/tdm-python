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
                    if len(node.args.args) > 0:
                        raise Exception(f"Unexpected arguments in onevent handler {event_name}")
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
                ast.LShift: ("<<", self.PRI_SHIFT),
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
tmp[{tmp_offset}] = 1
else
tmp[{tmp_offset}] = 0
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
        elif isinstance(node, ast.Call):
            # a very few set of functions
            if not isinstance(node.func, ast.Name):
                raise Exception("Function call where function is not a name")
            fun_name = node.func.id
            if fun_name == "abs":
                if len(node.args) != 1:
                    raise Exception("Wrong number of arguments for abs")
                code, aux_st, tmp_req, is_boolean = self.compile_expr(node.args[0], self.PRI_COMMA, tmp_req)
                aux_statements += aux_st
                code = f"abs({code})"
                return code, aux_statements, tmp_req, False
            else:
                raise Exception(f"Unknown function {fun_name}")
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
tmp[{tmp_req}] = 1
else
tmp[{tmp_req}] = 0
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
tmp[{tmp_offset}] = 1
else
tmp[{tmp_offset}] = 0
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

    def compile_node(self, node, tmp_req=0, var0=None):
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
tmp[{tmp_req}] = 1
else
tmp[{tmp_req}] = 0
end
"""
                    index_value = "tmp[{tmp_req}]"
                    tmp_req += 1
                target += "[" + index_value + "]"
            if is_boolean:
                # convert boolean to number
                code += f"""if {value} then
{target} = 1
else
{target} = 0
end
"""
                tmp_req = max(tmp_req, 1)
            else:
                code += f"{target} = {value}\n"
            if isinstance(node.value, ast.List):
                # var = [...]
                target_size = len(node.value.elts)
            elif isinstance(node.value, ast.Name):
                # var1 = var2: inherit size
                name_right = self.decode_attr(node.value)
                target_size = var0[name_right] if var0 is not None and name_right in var0 else None
            else:
                target_size = None
            return code, {target: target_size} if index is None else {}, tmp_req
        elif isinstance(node, ast.AugAssign):
            op_str = {
                ast.Add: "+",
                ast.BitAnd: "&",
                ast.BitOr: "|",
                ast.BitXor: "^",
                ast.FloorDiv: "/",
                ast.LShift: "<<",
                ast.Mod: "%",
                ast.Mult: "*",
                ast.RShift: ">>",
                ast.Sub: "-",
            }[type(node.op)]
            target, index = self.decode_target(node.target)
            value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.value, self.PRI_NUMERIC, tmp_req)
            code += aux_statements
            if index is not None:
                index_value, aux_statements, tmp_req, is_index_boolean = self.compile_expr(index, self.PRI_NUMERIC, tmp_req)
                code += aux_statements
                if is_index_boolean:
                    code += f"""if {index_value} then
tmp[{tmp_req}] = 1
else
tmp[{tmp_req}] = 0
end
"""
                    index_value = "tmp[{tmp_req}]"
                    tmp_req += 1
                target += "[" + index_value + "]"
            if is_boolean:
                # convert boolean to number
                code += f"""if {value} then
{target} {op_str}= 1
else
{target} {op_str}= 0
end
"""
                tmp_req = max(tmp_req, 1)
            else:
                code += f"{target} {op_str}= {value}\n"
            return code, {}, tmp_req
        elif isinstance(node, ast.Expr):
            # plain expression without assignment
            expr = node.value
            # hard-coded ... (ellipsis, alias of None, synonym of pass)
            if isinstance(expr, ast.Ellipsis):
                return "", {}, tmp_req
            # hard-coded emit(name, params...)
            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
                if expr.func.id == "emit":
                    if (len(expr.args) < 1 or
                        not isinstance(expr.args[0], ast.Constant) or
                        not isinstance(expr.args[0].value, str)):
                        print(expr.args[0])
                        raise Exception("Bad event name in emit")
                    event_name = expr.args[0].value
                    code = f"emit {event_name}"
                    aux_statements = ""
                    if len(expr.args) > 1:
                        tmp_req0 = tmp_req
                        for i in range(len(expr.args) - 1):
                            value, aux_st, tmp_req1, is_boolean = self.compile_expr(expr.args[1 + i], self.PRI_NUMERIC, tmp_req0)
                            aux_statements += aux_st
                            code += " [" if i == 0 else ", "
                            code += value
                            tmp_req = max(tmp_req, tmp_req1)
                        code += "]"
                    code = aux_statements + code
                    return code, {}, tmp_req
            # parse expression
            value, aux_statements, tmp_req, is_boolean = self.compile_expr(expr, self.PRI_NUMERIC, tmp_req)
            # ignore it because nothing can cause side effects now
            return "", {}, tmp_req
        elif isinstance(node, ast.For):
            # for var in range(...): ...
            if not isinstance(node.target, ast.Name):
                raise Exception("for loop with unsupported target (not a plain variable)")
            if (not isinstance(node.iter, ast.Call) or
                not isinstance(node.iter.func, ast.Name) or
                node.iter.func.id != "range" or
                len(node.iter.args) < 1 or len(node.iter.args) > 3):
                raise Exception("for loop with unsupported iterator (not range)")
            range_args = node.iter.args
            target = self.decode_attr(node.target)
            var = {target: None}
            if len(range_args) == 1:
                # for var in range(a): ...
                # stores limit a in tmp[tmp_offset]
                tmp_offset = tmp_req
                value, aux_statements, tmp_req, is_boolean = self.compile_expr(range_args[0], self.PRI_NUMERIC, tmp_offset)
                tmp_req = max(tmp_req, tmp_offset + 1)
                code += aux_statements
                code += f"""{target} = 0
tmp[{tmp_offset}] = {value}
while {target} < tmp[{tmp_offset}] do
"""
            elif len(range_args) == 2:
                # for var in range(a, b)
                # stores limit b in tmp[tmp_offset]
                tmp_offset = tmp_req
                value, aux_statements, tmp_req, is_boolean = self.compile_expr(range_args[0], self.PRI_NUMERIC, tmp_offset)
                tmp_req = max(tmp_req, tmp_offset + 1)
                code += aux_statements
                code += f"""{target} = {value}
"""
                value, aux_statements, tmp_req1, is_boolean = self.compile_expr(range_args[1], self.PRI_NUMERIC, tmp_offset)
                tmp_req = max(tmp_req, tmp_req1)
                code += aux_statements
                code += f"""tmp[{tmp_offset}] = {value}
while {target} < tmp[{tmp_offset}] do
"""
            else:
                # for var in range(a, b, c)
                # stores limit b in tmp[tmp_offset] and step c in tmp[tmp_offset+1]
                tmp_offset = tmp_req
                value, aux_statements, tmp_req, is_boolean = self.compile_expr(range_args[0], self.PRI_NUMERIC, tmp_offset)
                tmp_req = max(tmp_req, tmp_offset + 2)
                code += aux_statements
                code += f"""{target} = {value}
"""
                value, aux_statements, tmp_req1, is_boolean = self.compile_expr(range_args[1], self.PRI_NUMERIC, tmp_offset)
                tmp_req = max(tmp_req, tmp_req1)
                code += aux_statements
                code += f"""tmp[{tmp_offset}] = {value}
"""
                value, aux_statements, tmp_req1, is_boolean = self.compile_expr(range_args[2], self.PRI_NUMERIC, tmp_offset + 1)
                tmp_req = max(tmp_req, tmp_req1)
                code += aux_statements
                code += f"""tmp[{tmp_offset + 1}] = {value}
while {target} < tmp[{tmp_offset}] do
"""
            body, var1, tmp_req1 = self.compile_node_array(node.body, tmp_offset, var0=var0)
            code += body
            self.check_var_size(var, var1)
            var = {**var, **var1}
            tmp_req = max(tmp_req, tmp_req1)
            if len(range_args) <= 2:
                # just increment target
                code += f"""{target}++
"""
            else:
                # increment target by step
                code += f"""{target} += tmp[{tmp_offset + 1}]
"""
            code += """end
"""
            if node.orelse is not None and len(node.orelse) > 0:
                # else clause always executed b/c break is not supported
                body, var1, tmp_req1 = self.compile_node_array(node.orelse, tmp_offset, var0=var0)
                code += body
                self.check_var_size(var, var1)
                var = {**var, **var1}
                tmp_req = max(tmp_req, tmp_req1)
            return code, var, tmp_req
        elif isinstance(node, ast.Global):
            # ignored, but should be used in functions for forward compatibility
            return "", {}, tmp_req
        elif isinstance(node, ast.If):
            tmp_offset = tmp_req
            test_value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.test, self.PRI_LOW, tmp_req)
            code += aux_statements
            code += f"""if {test_value}{"" if is_boolean else " != 0"} then
"""
            body, var, tmp_req1 = self.compile_node_array(node.body, tmp_offset, var0=var0)
            code += body
            tmp_req = max(tmp_req, tmp_req1)
            while len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # "if" node as single element of orelse: elif
                node = node.orelse[0]
                test_value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.test, self.PRI_LOW, tmp_req)
                code += aux_statements
                code += f"""elseif {test_value}{"" if is_boolean else " != 0"} then
"""
                body, var1, tmp_req1 = self.compile_node_array(node.body, tmp_offset, var0=var0)
                code += body
                self.check_var_size(var, var1)
                var = {**var, **var1}
                tmp_req = max(tmp_req, tmp_req1)
            if len(node.orelse) > 0:
                # anything else in orelse: else
                code += """else
"""
                body, var1, tmp_req1 = self.compile_node_array(node.orelse, tmp_offset, var0=var0)
                code += body
                self.check_var_size(var, var1)
                var = {**var, **var1}
                tmp_req = max(tmp_req, tmp_req1)
            code += """end
"""
            return code, var, tmp_req
        elif isinstance(node, ast.Pass):
            return "", {}, tmp_req
        elif isinstance(node, ast.Return):
            if node.value is not None:
                raise Exception("Unsupported value in return statement")
            code += """return
"""
            return code, {}, tmp_req
        elif isinstance(node, ast.While):
            tmp_offset = tmp_req
            test_value, aux_statements, tmp_req, is_boolean = self.compile_expr(node.test, self.PRI_LOW, tmp_req)
            code += aux_statements
            code += f"""while {test_value}{"" if is_boolean else " != 0"} do
"""
            body, var, tmp_req1 = self.compile_node_array(node.body, tmp_offset, var0=var0)
            code += body
            tmp_req = max(tmp_req, tmp_req1)
            code += aux_statements  # to evaluate condition
            code += """end
"""
            if node.orelse is not None and len(node.orelse) > 0:
                # else clause always executed b/c break is not supported
                body, var1, tmp_req1 = self.compile_node_array(node.orelse, tmp_offset, var0=var0)
                code += body
                self.check_var_size(var, var1)
                var = {**var, **var1}
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

    def compile_node_array(self, node_array, tmp_req=0, var0=None):
        code = ""
        var = var0 or {}
        tmp_req0 = tmp_req
        for node in node_array:
            c, v, tmp_req1 = self.compile_node(node, tmp_req0, var0=var)
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
            event_output_src, var1, tmp_req1 = self.compile_node_array(event_handlers[event_name].body, tmp_offset, var0=var)
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

    @staticmethod
    def pretty_print(src):
        """Indent Aseba code
        """

        level = 0

        def indent(line):
            nonlocal level
            # expect keyword+space+whatever
            keyword = line.split(" ")[0].replace(":", "")
            next_level = level
            if keyword in {"onevent", "sub"}:
                level = 0
                next_level = 1
            elif keyword in {"for", "if", "when", "while"}:
                next_level = level + 1
            elif keyword in {"else", "elseif"}:
                next_level = level
                level = max(level - 1, 0)
            elif keyword == "end":
                level = max(level - 1, 0)
                next_level = level
            line = level * "\t" + line
            level = next_level
            return line

        src = "\n".join([
            indent(line)
            for line in src.split("\n")
        ])
        return src

    def get_output(self):
        return self.pretty_print(self.output_src)


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
