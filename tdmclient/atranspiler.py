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


class Context:

    def __init__(self, parent_context=None, function_name=None, function_def=None, is_onevent=False):
        # reference to base context for functions or None for base context itself
        self.parent_context = parent_context

        # function name, to be used as the namespace of local variables
        self.function_name = function_name

        # ast.FunctionDef node for function
        self.function_def = function_def

        # whether it's an event handler (decorator @onevent)
        self.is_onevent = is_onevent

        # size of local variables
        self.var = {}

        # add function arguments (all are assumed to be scalar)
        if function_def is not None:
            for arg in function_def.args.args:
                self.var[arg.arg] = None

        # set of variables declared as global
        self.global_var = set()

        # function definitions indexed by function name (nodes ast.FunctionDef)
        self.functions = {}

        self.has_return_val = None
        self.tmp_req = 0
        self.tmp_req_current_expr = 0

        # set of called functions, used for dependencies and recursivity check
        self.called_functions = set()

    def is_global(self, name):
        """Check if a variable is global or not.
        """
        return name not in self.var or name in ATranspiler.PREDEFINED_VARIABLES

    def var_str(self, name):
        """Convert a variable name to its string representation in output
        source code.
        """
        return name if self.function_name is None or self.is_global(name) else f"_{self.function_name}_{name}"

    def tmp_var_str(self, index):
        """Convert a temporary variable specified by index to its string
        representation in output source code.
        """
        # _tmp is always local to avoid interference with caller's
        name = "_tmp" if self.function_name is None else f"_{self.function_name}__tmp"
        return f"{name}[{index}]"

    def declare_global(self, name):
        """Declare a global variable.
        """
        if name in self.var:
            raise Exception(f"Variable {name} declared global after being assigned to")
        self.global_var.add(name)

    def declare_var(self, name, size=None):
        """Declare a variable with its size (array size, or None if scalar).
        """
        var = self.parent_context.var if name in self.global_var and self.parent_context is not None else self.var
        if name in var:
            if (size != var[name] or
                name in ATranspiler.PREDEFINED_VARIABLES and size != ATranspiler.PREDEFINED_VARIABLES[name]):
                raise Exception(f"Incompatible sizes for list assignment to {name}")
        else:
            var[name] = size

    def var_array_size(self, name):
        """Return size if name is a local or global array variable,
        None if it is a local or global scalar, or False if unknown.
        """
        var = (ATranspiler.PREDEFINED_VARIABLES if name in ATranspiler.PREDEFINED_VARIABLES
               else self.parent_context.var if name in self.global_var and self.parent_context is not None
               else self.var)
        return False if name not in var else var[name]

    def var_declarations(self):
        """Output source code for local variable declarations.
        """
        return "".join([
            f"var {self.var_str(name)}{f'[{self.var[name]}]' if self.var[name] is not None else ''}\n"
            for name in self.var
            if name not in ATranspiler.PREDEFINED_VARIABLES
        ])

    def reset_tmp_req_current_expr(self):
        """Reset the requirements for temporary variables for the current
        expression.
        """
        self.tmp_req_current_expr = 0

    def request_tmp(self, total):
        """Request at least the specified amount of temporary variables.
        """
        if total > self.tmp_req:
            self.tmp_req = total
            self.var["_tmp"] = self.tmp_req

    def request_tmp_expr(self, n=1):
        """Request temporary variable(s) and return its index.
        """
        tmp_offset = self.tmp_req_current_expr
        self.tmp_req_current_expr += n
        self.request_tmp(self.tmp_req_current_expr)
        return tmp_offset

    def freeze_return_type(self):
        """Freeze the return type (void if no return statement).
        """
        if self.has_return_val is None:
            self.has_return_val = False

    def get_function_definition(self, fun_name):
        """Get a function definition in the current or parent context.
        """
        return (self.functions[fun_name] if fun_name in self.functions
                else self.parent_context.functions[fun_name] if self.parent_context is not None and fun_name in self.parent_context.functions
                else None)

    def is_recursive(self, fun_dict):
        """Check if function or what it calls is recursive.
        """

        # for each function, set of functions called directly or indirectly
        connections = {}

        # fill connections starting for function fun_name
        # return True and exit early if recursive
        def connect(fun_name):
            if fun_name not in connections:
                c = fun_dict[fun_name].called_functions.copy()
                for f in fun_dict[fun_name].called_functions:
                    if f == self.function_name or connect(f):
                        return True
                    c |= connections[f]
                connections[fun_name] = c
            return False

        for fun_name in self.called_functions:
            if connect(fun_name):
                return fun_name

        return None


class PredefinedFunction:
    """Transpilation information for predefined functions.
    """

    def __init__(self, name, argin, nargout, fun):
        """argin: arrays of False for scalars or True for arrays;
        nargout: number of scalar outputs (unpacked to scalar variables or
        used in expression if nargout is 1)
        """
        self.name = name
        self.argin = argin
        self.nargout = nargout
        self.fun = fun

    def get_code(self, atranspiler, context, args):
        aux_statements = ""
        arg_code = []
        for arg in args:
            value, aux_st, _ = atranspiler.compile_expr(arg, context, ATranspiler.PRI_NUMERIC)
            aux_statements += aux_st
            arg_code.append(value)
        values, aux_st = self.fun(context, arg_code)
        aux_statements += aux_st
        return values, aux_statements


class ATranspiler:
    """Transpiler from a subset of Python3 to Aseba.
    """

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

        self.predefined_function_dict = {}

        def predefined_function(name, argin, nargout=0):
            def register(fun):
                self.predefined_function_dict[name] = PredefinedFunction(name, argin, nargout, fun)
                return fun
            return register

        @predefined_function("nf.math.copy", [True, True])
        def math_copy(context, args):
            return None, f"""call math.copy({args[0]}, {args[1]})
"""

        @predefined_function("nf.math.fill", [True, False])
        def math_fill(context, args):
            return None, f"""call math.fill({args[0]}, {args[1]})
"""

        @predefined_function("nf.math.addscalar", [True, True, False])
        def math_addscalar(context, args):
            return None, f"""call math.addscalar({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf.math.add", [True, True, True])
        def math_add(context, args):
            return None, f"""call math.add({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf.math.sub", [True, True, True])
        def math_sub(context, args):
            return None, f"""call math.sub({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf.math.mul", [True, True, True])
        def math_mul(context, args):
            return None, f"""call math.mul({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf.math.div", [True, True, True])
        def math_div(context, args):
            return None, f"""call math.div({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf.math.min", [True, True, True])
        def math_min(context, args):
            return None, f"""call math.min({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("math.min", [False, False], 1)
        def fun_math_min(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.min({var_str}, [{args[0]}], [{args[1]}])
"""

        @predefined_function("nf.math.max", [True, True, True])
        def math_max(context, args):
            return None, f"""call math.max({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("math.max", [False, False], 1)
        def fun_math_max(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.max({var_str}, [{args[0]}], [{args[1]}])
"""

        @predefined_function("nf.math.clamp", [True, True, True, True])
        def math_clamp(context, args):
            return None, f"""call math.clamp({args[0]}, {args[1]}, {args[2]}, {args[3]})
"""

        @predefined_function("math.clamp", [False, False, False], 1)
        def fun_math_clamp(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.clamp({var_str}, [{args[0]}], [{args[1]}, {args[2]}])
"""

        @predefined_function("nf.math.rand", [True])
        def math_rand(context, args):
            return None, f"""call math.rand({args[0]})
"""

        @predefined_function("math.rand", [], 1)
        def fun_math_rand(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.rand({var_str})
"""

        @predefined_function("nf.math.sort", [True])
        def math_sort(context, args):
            return None, f"""call math.sort({args[0]})
"""

        @predefined_function("nf.math.muldiv", [True, True, True, True])
        def math_muldiv(context, args):
            return None, f"""call math.muldiv({args[0]}, {args[1]}, {args[2]}, {args[3]})
"""

        @predefined_function("math.muldiv", [False, False, False], 1)
        def fun_math_muldiv(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.muldiv({var_str}, [{args[0]}], [{args[1]}, {args[2]}])
"""

        @predefined_function("nf.math.atan2", [True, True, True])
        def math_atan2(context, args):
            return None, f"""call math.atan2({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("math.atan2", [False, False], 1)
        def fun_math_atan2(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.atan2({var_str}, [{args[0]}], [{args[1]}])
"""

        @predefined_function("nf.math.sin", [True, True])
        def math_sin(context, args):
            return None, f"""call math.sin({args[0]}, {args[1]})
"""

        @predefined_function("math.sin", [False], 1)
        def fun_math_sin(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.sin({var_str}, [{args[0]}])
"""

        @predefined_function("nf.math.cos", [True, True])
        def math_cos(context, args):
            return None, f"""call math.cos({args[0]}, {args[1]})
"""

        @predefined_function("math.cos", [False], 1)
        def fun_math_cos(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.cos({var_str}, [{args[0]}])
"""

        @predefined_function("nf.math.rot2", [True, True, False])
        def math_rot2(context, args):
            return None, f"""call math.rot2({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf.math.sqrt", [True, True])
        def math_sqrt(context, args):
            return None, f"""call math.sqrt({args[0]}, {args[1]})
"""

        @predefined_function("math.sqrt", [False], 1)
        def fun_math_sqrt(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.sqrt({var_str}, [{args[0]}])
"""

    def set_source(self, source):
        """Set the Python source code and reset transpilation.
        """
        self.src = source
        self.ast = None
        self.output_src = None

    def decode_attr(self, node):
        """Decode an attribute or name and convert it to a dotted name.
        """
        name = ""
        while isinstance(node, ast.Attribute):
            name = "." + node.attr + name
            node = node.value
        if isinstance(node, ast.Name):
            name = node.id + name
        else:
            raise Exception("Invalid name")
        return name

    def split(self, parent_context):
        """Split the Python source code into top-level source code, which is
        returned, and function definitions, which are stored into parent_context.
        """
        top_code = []
        for node in self.ast.body:
            if isinstance(node, ast.FunctionDef):
                is_onevent = False
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Name):
                        raise Exception(f"Unsupported function decorator type {ast.dump(decorator)}")
                    if decorator.id != "onevent":
                        raise Exception(f'Unsupported function decorator "{decorator.id}"')
                    is_onevent = True
                if node.name in parent_context.functions:
                    raise Exception(f"Function {node.name} defined multiple times")
                elif len(node.args.args) > 0:
                    if is_onevent:
                        raise Exception(f"Unexpected arguments in @onevent function {node.name}")
                    if len(node.args.defaults) > 0:
                        raise Exception(f"Unsupported default values for arguments of {node.name}")
                    if len({a.arg for a in node.args.args}) < len(node.args.args):
                        raise Exception(f"Multiple arguments with the same name in function {node.name}")
                if node.args.vararg is not None:
                    raise Exception(f"Unsupported varargs in arguments of {node.name}")
                if node.args.kwarg is not None:
                    raise Exception(f"Unsupported kwargs in arguments of {node.name}")
                parent_context.functions[node.name] = Context(parent_context=parent_context, function_name=node.name, function_def=node, is_onevent=is_onevent)
            else:
                top_code.append(node)

        return top_code

    # http://wiki.thymio.org/en:asebalanguage
    PRI_LOW = 0
    PRI_EXPR = 1  # ast.Expr
    PRI_ASSIGN = 2
    PRI_COMMA = 3
    PRI_LOGICAL_OR = 4
    PRI_LOGICAL_AND = 5
    PRI_LOGICAL_NOT = 6
    PRI_COMPARISON = 7
    PRI_NUMERIC = 8
    PRI_BINARY_OR = 9
    PRI_BINARY_XOR = 10
    PRI_BINARY_AND = 11
    PRI_SHIFT = 12
    PRI_ADD = 13
    PRI_MOD = 14
    PRI_MULT = 15
    PRI_ABS = 16
    PRI_BINARY_NOT = 17
    PRI_UNARY_MINUS = 18
    PRI_HIGH = 100

    def compile_expr(self, node, context, priority_container=PRI_LOW):
        """Compile an expression or subexpression.
        Return the expression, additional statements to calculate auxiliary values,
        and whether result is boolean.
        """
        code = None
        aux_statements = ""
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
            left, aux_st, _ = self.compile_expr(node.left, context, priority)
            aux_statements += aux_st
            right, aux_st, _ = self.compile_expr(node.right, context, priority)
            aux_statements += aux_st
            code = f"{left} {op_str} {right}"
        elif isinstance(node, ast.BoolOp):
            # with shortcuts, useful e.g. to avoid out-of-bound array indexing
            # result is not pretty b/c of aseba's idea of what's acceptable
            op = node.op
            cmp = "!=" if isinstance(op, ast.And) else "=="
            tmp_offset = context.request_tmp_expr()
            for i in range(len(node.values)):
                value, aux_st, is_value_boolean = self.compile_expr(node.values[i], context, self.PRI_ASSIGN)
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
                    aux_statements += f"""{context.tmp_var_str(tmp_offset)} = {value}
"""
                # continue evaluating terms if true (and) or false (or)
                if i + 1 < len(node.values):
                    aux_statements += f"""if {context.tmp_var_str(tmp_offset)} {cmp} 0 then
"""
            for i in range(len(node.values) - 1):
                aux_statements += """end
"""
            code = context.tmp_var_str(tmp_offset)
            is_boolean = False
        elif isinstance(node, ast.Call):
            fun_name = self.decode_attr(node.func)
            function_def = context.get_function_definition(fun_name)
            if function_def is not None:
                context.called_functions.add(fun_name)
                # set arguments (assign values to function's local variables)
                if len(node.args) > len(function_def.function_def.args.args):
                    raise Exception("Too many arguments in call to function {fun_name}")
                elif len(node.args) < len(function_def.function_def.args.args):
                    raise Exception("Too few arguments in call to function {fun_name}")
                for i, arg_def in enumerate(function_def.function_def.args.args):
                    arg = node.args[i]
                    code, aux_st, is_boolean = self.compile_expr(arg, context, self.PRI_COMMA)
                    aux_statements += aux_st
                    aux_statements += f"""{function_def.var_str(arg_def.arg)} = {code}
"""
                # call
                aux_statements += f"""callsub {fun_name}
"""
                if function_def.has_return_val:
                    tmp_offset = context.request_tmp_expr()
                    aux_statements += f"""{context.tmp_var_str(tmp_offset)} = {function_def.tmp_var_str(0)}
"""
                    code = context.tmp_var_str(tmp_offset)
                elif function_def.has_return_val == False:
                    # no return value: must not be called in a subexpression
                    if priority_container != self.PRI_EXPR:
                        raise Exception("Function without return value called in an expression")
                return code, aux_statements, False
            elif fun_name in self.predefined_function_dict:
                predefined_function = self.predefined_function_dict[fun_name]
                if len(node.args) != len(predefined_function.argin):
                    raise Exception(f"Wrong number of arguments for function {fun_name}")
                if predefined_function.nargout != 1:
                    raise Exception(f"Wrong number of results for function {fun_name}")
                values, aux_statements = predefined_function.get_code(self, context, node.args)
                return values[0], aux_statements, False
            else:
                # hard-coded functions
                if fun_name == "abs":
                    if len(node.args) != 1:
                        raise Exception("Wrong number of arguments for abs")
                    code, aux_st, is_boolean = self.compile_expr(node.args[0], context, self.PRI_COMMA)
                    aux_statements += aux_st
                    code = f"abs({code})"
                    return code, aux_statements, False
                elif fun_name == "len":
                    if len(node.args) != 1:
                        raise Exception("Wrong number of arguments for len")
                    if isinstance(node.args[0], ast.Name):
                        len_arg_size = context.var_array_size(node.args[0].id)
                        code = f"{len_arg_size}" if len_arg_size is not None else "0"
                    elif isinstance(node.args[0], ast.List):
                        code = f"{len(node.args[0].elts)}"
                    else:
                        raise Exception("Type of argument of len is not a list")
                    return code, aux_statements, False
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
            left, aux_st, _ = self.compile_expr(node.left, context, self.PRI_NUMERIC)
            aux_statements += aux_st
            right, aux_st, _ = self.compile_expr(node.comparators[0], context, self.PRI_NUMERIC)
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
        elif isinstance(node, ast.IfExp):
            tmp_offset = context.request_tmp_expr()
            value, aux_st, is_boolean = self.compile_expr(node.test, context, self.PRI_ASSIGN)
            aux_statements += aux_st
            aux_statements += f"""if {value}{"" if is_boolean else " != 0"} then
"""
            value, aux_st, is_boolean = self.compile_expr(node.body, context, self.PRI_NUMERIC)
            aux_statements += aux_st
            aux_statements += f"""{context.tmp_var_str(tmp_offset)} = {value}
else
"""
            value, aux_st, is_boolean = self.compile_expr(node.orelse, context, self.PRI_NUMERIC)
            aux_statements += aux_st
            aux_statements += f"""{context.tmp_var_str(tmp_offset)} = {value}
end
"""
            code = context.tmp_var_str(tmp_offset)
            is_boolean = False
        elif isinstance(node, ast.List):
            if priority_container > self.PRI_ASSIGN:
                raise Exception("List not supported in expression")
            for el in node.elts:
                el_code, aux_st, is_boolean = self.compile_expr(el, context, self.PRI_NUMERIC)
                aux_statements += aux_st
                if code is None:
                    code = "[" + el_code
                else:
                    code += ", " + el_code
            code += "]"
            return code, aux_statements, False
        elif isinstance(node, ast.Name):
            if isinstance(context.var_array_size(node.id), int):
                raise Exception(f"List variable {node.id} used in expression")
            code = context.var_str(node.id)
        elif isinstance(node, ast.Subscript):
            name = self.decode_attr(node.value)
            if context.var_array_size(name) is None:
                raise Exception(f"Indexing of variable {name} which is not a list")
            index = node.slice.value
            index_value, aux_st, is_index_boolean = self.compile_expr(index, context, self.PRI_NUMERIC)
            if is_index_boolean:
                tmp_offset = context.request_tmp_expr()
                aux_st += f"""if {index_value} then
{context.tmp_var_str(tmp_offset)} = 1
else
{context.tmp_var_str(tmp_offset)} = 0
end
"""
                index_value = context.tmp_var_str(tmp_offset)
            aux_statements += aux_st
            code = f"{name}[{index_value}]"
        elif isinstance(node, ast.UnaryOp):
            op = node.op
            if isinstance(op, ast.UAdd):
                priority = self.PRI_ADD
                code, aux_st, is_boolean = self.compile_expr(node.operand, context, priority)
                aux_statements += aux_st
            elif isinstance(op, ast.Invert):
                priority = self.PRI_BINARY_NOT
                operand, aux_st, is_boolean = self.compile_expr(node.operand, context, priority)
                aux_statements += aux_st
                code = "~" + operand
            elif isinstance(op, ast.Not):
                priority = self.PRI_LOGICAL_NOT
                operand, aux_st, is_boolean = self.compile_expr(node.operand, context, priority)
                if is_boolean:
                    code = "not " + operand
                else:
                    code = operand + " == 0"
                    is_boolean = True
            elif isinstance(op, ast.USub):
                priority = self.PRI_UNARY_MINUS
                operand, aux_st, is_boolean = self.compile_expr(node.operand, context, priority)
                aux_statements += aux_st
                code = "-" + operand
            else:
                raise Exception(f"Unsupported unary op {op}")
        else:
            raise Exception(f"Node {ast.dump(node)} not implemented")

        if priority < self.PRI_NUMERIC and priority_container >= self.PRI_NUMERIC:
            # work around aseba's idea of what's acceptable
            # (no boolean in arithmetic subexpressions or variables)
            tmp_offset = context.request_tmp_expr()
            aux_statements += f"""if {code} then
{context.tmp_var_str(tmp_offset)} = 1
else
{context.tmp_var_str(tmp_offset)} = 0
end
"""
            return context.tmp_var_str(tmp_offset), aux_statements, False
        elif priority < priority_container:
            return "(" + code + ")", aux_statements, is_boolean
        else:
            return code, aux_statements, is_boolean

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

    def compile_node(self, node, context, var0=None):
        """Compile an ast statement node.
        """
        code = ""
        context.reset_tmp_req_current_expr()
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise Exception("Unsupported assignment to multiple targets")
            target, index = self.decode_target(node.targets[0])
            target_str = context.var_str(target)
            if isinstance(node.value, ast.List):
                if index is not None:
                    raise Exception("List assigned to indexed variable")
                value, aux_statements, is_boolean = self.compile_expr(node.value, context, self.PRI_ASSIGN)
            else:
                value, aux_statements, is_boolean = self.compile_expr(node.value, context, self.PRI_NUMERIC)
            code += aux_statements
            if index is not None:
                tmp_offset = context.request_tmp_expr()
                index_value, aux_statements, is_index_boolean = self.compile_expr(index, context, self.PRI_NUMERIC)
                code += aux_statements
                if is_index_boolean:
                    code += f"""if {index_value} then
{context.tmp_var_str(tmp_offset)} = 1
else
{context.tmp_var_str(tmp_offset)} = 0
end
"""
                    index_value = context.tmp_var_str(tmp_offset)
                target_str += "[" + index_value + "]"
            if is_boolean:
                # convert boolean to number
                code += f"""if {value} then
{target_str} = 1
else
{target_str} = 0
end
"""
            else:
                code += f"{target_str} = {value}\n"
            if isinstance(node.value, ast.List):
                # var = [...]
                target_size = len(node.value.elts)
                context.declare_var(target, target_size)
            elif isinstance(node.value, ast.Name):
                # var1 = var2: inherit size
                name_right = self.decode_attr(node.value)
                target_size = var0[name_right] if var0 is not None and name_right in var0 else None
                context.declare_var(target, target_size)
            elif index is None:
                context.declare_var(target)
            return code
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
            target_str = context.var_str(target)
            value, aux_statements, is_boolean = self.compile_expr(node.value, context, self.PRI_NUMERIC)
            code += aux_statements
            if index is not None:
                index_value, aux_statements, is_index_boolean = self.compile_expr(index, context, self.PRI_NUMERIC)
                code += aux_statements
                if is_index_boolean:
                    tmp_offset = context.request_tmp_expr()
                    code += f"""if {index_value} then
{context.tmp_var_str(tmp_offset)} = 1
else
{context.tmp_var_str(tmp_offset)} = 0
end
"""
                    index_value = context.tmp_var_str(tmp_offset)
                target += "[" + index_value + "]"
            if is_boolean:
                # convert boolean to number
                code += f"""if {value} then
{target_str} {op_str}= 1
else
{target_str} {op_str}= 0
end
"""
            else:
                code += f"{target_str} {op_str}= {value}\n"
            return code
        elif isinstance(node, ast.Expr):
            # plain expression without assignment
            expr = node.value
            # hard-coded ... (ellipsis, alias of None, synonym of pass)
            if isinstance(expr, ast.Ellipsis):
                return ""
            # hard-coded constants, such as strings used for documentation
            if isinstance(expr, ast.Constant):
                return ""
            # special functions
            if isinstance(expr, ast.Call):
                fun_name = self.decode_attr(expr.func)
                if fun_name in self.predefined_function_dict:
                    # will ignore any output
                    predefined_function = self.predefined_function_dict[fun_name]
                    if len(expr.args) != len(predefined_function.argin):
                        raise Exception(f"Wrong number of arguments for function {fun_name}")
                    _, aux_statements = predefined_function.get_code(self, context, expr.args)
                    return aux_statements
                elif fun_name == "emit":
                    # hard-coded emit(name, params...)
                    if (len(expr.args) < 1 or
                        not isinstance(expr.args[0], ast.Constant) or
                        not isinstance(expr.args[0].value, str)):
                        raise Exception("Bad event name in emit")
                    event_name = expr.args[0].value
                    code = f"emit {event_name}"
                    aux_statements = ""
                    if len(expr.args) > 1:
                        for i in range(len(expr.args) - 1):
                            value, aux_st, is_boolean = self.compile_expr(expr.args[1 + i], context, self.PRI_NUMERIC)
                            aux_statements += aux_st
                            code += " [" if i == 0 else ", "
                            code += value
                        code += "]"
                    code = aux_statements + code
                    return code
            # parse expression
            value, aux_statements, is_boolean = self.compile_expr(expr, context, self.PRI_EXPR)
            # ignore result
            return aux_statements
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
            target_str = context.var_str(target)
            context.declare_var(target)
            if len(range_args) == 1:
                # for var in range(a): ...
                # stores limit a in tmp[tmp_offset]
                tmp_offset = context.request_tmp_expr()
                value, aux_statements, is_boolean = self.compile_expr(range_args[0], context, self.PRI_NUMERIC)
                code += aux_statements
                code += f"""{target_str} = 0
{context.tmp_var_str(tmp_offset)} = {value}
while {target_str} < {context.tmp_var_str(tmp_offset)} do
"""
            elif len(range_args) == 2:
                # for var in range(a, b)
                # stores limit b in tmp[tmp_offset]
                tmp_offset = context.request_tmp_expr()
                value, aux_statements, is_boolean = self.compile_expr(range_args[0], context, self.PRI_NUMERIC)
                code += aux_statements
                code += f"""{target_str} = {value}
"""
                value, aux_statements, is_boolean = self.compile_expr(range_args[1], context, self.PRI_NUMERIC)
                code += aux_statements
                code += f"""{context.tmp_var_str(tmp_offset)} = {value}
while {target_str} < {context.tmp_var_str(tmp_offset)} do
"""
            else:
                # for var in range(a, b, c)
                # stores limit b in tmp[tmp_offset] and step c in tmp[tmp_offset+1]
                tmp_offset = context.request_tmp_expr(2)
                value, aux_statements, is_boolean = self.compile_expr(range_args[0], context, self.PRI_NUMERIC)
                code += aux_statements
                code += f"""{target_str} = {value}
"""
                value, aux_statements, is_boolean = self.compile_expr(range_args[1], context, self.PRI_NUMERIC)
                code += aux_statements
                code += f"""{context.tmp_var_str(tmp_offset)} = {value}
"""
                value, aux_statements, is_boolean = self.compile_expr(range_args[2], context, self.PRI_NUMERIC)
                code += aux_statements
                code += f"""{context.tmp_var_str(tmp_offset + 1)} = {value}
while {target_str} < {context.tmp_var_str(tmp_offset)} do
"""
            body = self.compile_node_array(node.body, context)
            code += body
            if len(range_args) <= 2:
                # just increment target
                code += f"""{target_str}++
"""
            else:
                # increment target by step
                code += f"""{target_str} += {context.tmp_var_str(tmp_offset + 1)}
"""
            code += """end
"""
            if node.orelse is not None and len(node.orelse) > 0:
                # else clause always executed b/c break is not supported
                body = self.compile_node_array(node.orelse, context)
                code += body
            return code
        elif isinstance(node, ast.Global):
            for name in node.names:
                context.declare_global(name)
            return ""
        elif isinstance(node, ast.If):
            test_value, aux_statements, is_boolean = self.compile_expr(node.test, context, self.PRI_LOW)
            code += aux_statements
            code += f"""if {test_value}{"" if is_boolean else " != 0"} then
"""
            body = self.compile_node_array(node.body, context)
            code += body
            while len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # "if" node as single element of orelse: elif
                node = node.orelse[0]
                test_value, aux_statements, is_boolean = self.compile_expr(node.test, context, self.PRI_LOW)
                code += aux_statements
                code += f"""elseif {test_value}{"" if is_boolean else " != 0"} then
"""
                body = self.compile_node_array(node.body, context)
                code += body
            if len(node.orelse) > 0:
                # anything else in orelse: else
                code += """else
"""
                body = self.compile_node_array(node.orelse, context)
                code += body
            code += """end
"""
            return code
        elif isinstance(node, ast.Pass):
            return ""
        elif isinstance(node, ast.Return):
            if context.parent_context is None:
                raise Exception("Return outside function")
            if context.is_onevent and node.value is not None:
                raise Exception(f"Returned value in @onevent function {context.function_name}")
            if context.has_return_val is None:
                context.has_return_val = node.value is not None
            elif context.has_return_val != (node.value is not None):
                raise Exception(f"Inconsistent return values in function {context.function_name}")
            if node.value is not None:
                tmp_offset = context.request_tmp_expr()
                ret_value, aux_statements, _ = self.compile_expr(node.value, context, self.PRI_NUMERIC)
                code += aux_statements
                code += f"""{context.tmp_var_str(tmp_offset)} = {ret_value}
return
"""
            else:
                code += """return
"""
            return code
        elif isinstance(node, ast.While):
            test_value, aux_statements, is_boolean = self.compile_expr(node.test, context, self.PRI_LOW)
            code += aux_statements
            code += f"""while {test_value}{"" if is_boolean else " != 0"} do
"""
            body = self.compile_node_array(node.body, context)
            code += body
            code += aux_statements  # to evaluate condition
            code += """end
"""
            if node.orelse is not None and len(node.orelse) > 0:
                # else clause always executed b/c break is not supported
                body = self.compile_node_array(node.orelse, context)
                code += body
            return code
        else:
            raise Exception(f"Node {ast.dump(node)} not implemented")

    @staticmethod
    def check_var_size(var, var_new):
        """Check that the variable size is compatible with previous occurences
        if any.
        """
        for name in var_new:
            if (name in var and var_new[name] != var[name] or
                name in ATranspiler.PREDEFINED_VARIABLES and var_new[name] != ATranspiler.PREDEFINED_VARIABLES[name]):
                raise Exception(f"Incompatible sizes for list assignment to {name}")

    def compile_node_array(self, node_array, context):
        """Compile an array of ast statement nodes.
        """
        code = ""
        for node in node_array:
            c = self.compile_node(node, context)
            code += c
        return code

    def transpile(self):
        """Transpile whole Python source code.
        """

        # top-level context
        context_top = Context()

        # parse and split into top code and function definitions
        self.ast = ast.parse(self.src)
        top_code = self.split(context_top)

        # compile top-level code (first pass for global variable sizes)
        self.output_src = self.compile_node_array(top_code, context_top)

        # functions
        function_src = ""
        for fun_name in context_top.functions:
            # first pass to gather local variables into context_fun[.] (not declared global, but assigned to)
            # function return type isn't known yet (context.has_ret_value = None doesn't raise exceptions)
            event_output_src = self.compile_node_array(context_top.functions[fun_name].function_def.body, context_top.functions[fun_name])
            # set functions without return statements to void
            context_top.functions[fun_name].freeze_return_type()
            # second pass to produce transpiled code with correct local variable names
            fun_output_src = self.compile_node_array(context_top.functions[fun_name].function_def.body, context_top.functions[fun_name])
            function_src += f"""
{"onevent" if context_top.functions[fun_name].is_onevent else "sub"} {fun_name}
""" + fun_output_src

        # compile top-level code again, now that function return types are known
        self.output_src = self.compile_node_array(top_code, context_top) + function_src

        # check recursivity
        for fun_name in context_top.functions:
            if context_top.functions[fun_name].is_recursive(context_top.functions):
                raise Exception(f"Recursive function {fun_name}")

        # variable declarations
        var_decl = context_top.var_declarations()
        var_decl += "".join([
            context_top.functions[fun_name].var_declarations()
            for fun_name in context_top.functions
        ])
        if len(var_decl) > 0:
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
        """Get transpiled output.
        """
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
