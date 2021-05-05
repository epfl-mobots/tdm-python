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


class TranspilerError(Exception):
    """Error or issue in source code passed to transpiler.
    """

    def __init__(self, message, ast_node=None, syntax_error=None):
        super().__init__()
        self.message = message
        self.ast_node = ast_node
        self.syntax_error = syntax_error

    def __str__(self):
        output = self.message
        if self.ast_node is not None:
            output += f" (line {self.ast_node.lineno})"
        elif self.syntax_error is not None:
            output += f" (line {self.syntax_error.args[1][1]})"
        return output


class Context:
    """Global or function context.
    """

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
        return name not in self.var

    def var_str(self, name):
        """Convert a variable name to its string representation in output
        source code.
        """
        if self.function_name is None or self.is_global(name):
            return name.replace("_", ".") if name in ATranspiler.PREDEFINED_VARIABLES else name
        else:
            return f"_{self.function_name}_{name}"

    def tmp_var_str(self, index):
        """Convert a temporary variable specified by index to its string
        representation in output source code.
        """
        # _tmp is always local to avoid interference with caller's
        name = "_tmp" if self.function_name is None else f"_{self.function_name}__tmp"
        return f"{name}[{index}]"

    def declare_global(self, name, ast_node=None):
        """Declare a global variable.
        """
        if name in self.var:
            raise TranspilerError(f"variable {name} declared global after being assigned to", ast_node)
        self.global_var.add(name)

    def declare_var(self, name, size=None, ast_node=None):
        """Declare a variable with its size (array size, or None if scalar).
        """
        var = self.parent_context.var if name in self.global_var and self.parent_context is not None else self.var
        if name in var:
            if (size != var[name] or
                name in self.global_var and name in ATranspiler.PREDEFINED_VARIABLES and size != ATranspiler.PREDEFINED_VARIABLES[name]):
                raise TranspilerError(f"incompatible sizes for list assignment to {name}", ast_node)
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
            if self.parent_context is not None or name not in ATranspiler.PREDEFINED_VARIABLES
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

    def request_tmp_expr(self, count=1):
        """Request temporary variable(s) and return its index.
        """
        tmp_offset = self.tmp_req_current_expr
        self.tmp_req_current_expr += count
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
                connections_upd = fun_dict[fun_name].called_functions.copy()
                for fun in fun_dict[fun_name].called_functions:
                    if fun == self.function_name or connect(f):
                        return True
                    connections_upd |= connections[fun]
                connections[fun_name] = connections_upd
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
        """Get the code for the function call.
        """
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
        "button_backward": None,
        "button_center": None,
        "button_forward": None,
        "button_left": None,
        "button_right": None,
        "events_arg": 32,
        "events_source": None,
        "leds_bottom_left": 3,
        "leds_bottom_right": 3,
        "leds_circle": 8,
        "leds_top": 3,
        "mic_intensity": None,
        "mic_threshold": None,
        "motor_left_pwm": None,
        "motor_left_speed": None,
        "motor_left_target": None,
        "motor_right_pwm": None,
        "motor_right_speed": None,
        "motor_right_target": None,
        "prox_comm_rx": None,
        "prox_comm_tx": None,
        "prox_ground_ambient": 2,
        "prox_ground_delta": 2,
        "prox_ground_reflected": 2,
        "prox_horizontal": 7,
        "rc5_address": None,
        "rc5_command": None,
        "sd_present": None,
        "temperature": None,
        "timer_period": 2,
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

        @predefined_function("nf_math_copy", [True, True])
        def _math_copy(context, args):
            return None, f"""call math.copy({args[0]}, {args[1]})
"""

        @predefined_function("nf_math_fill", [True, False])
        def _math_fill(context, args):
            return None, f"""call math.fill({args[0]}, {args[1]})
"""

        @predefined_function("nf_math_addscalar", [True, True, False])
        def _math_addscalar(context, args):
            return None, f"""call math.addscalar({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf_math_add", [True, True, True])
        def _math_add(context, args):
            return None, f"""call math.add({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf_math_sub", [True, True, True])
        def _math_sub(context, args):
            return None, f"""call math.sub({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf_math_mul", [True, True, True])
        def _math_mul(context, args):
            return None, f"""call math.mul({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf_math_div", [True, True, True])
        def _math_div(context, args):
            return None, f"""call math.div({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf_math_min", [True, True, True])
        def _math_min(context, args):
            return None, f"""call math.min({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("math_min", [False, False], 1)
        def _fun_math_min(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.min({var_str}, [{args[0]}], [{args[1]}])
"""

        @predefined_function("nf_math_max", [True, True, True])
        def _math_max(context, args):
            return None, f"""call math.max({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("math_max", [False, False], 1)
        def _fun_math_max(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.max({var_str}, [{args[0]}], [{args[1]}])
"""

        @predefined_function("nf_math_clamp", [True, True, True, True])
        def _math_clamp(context, args):
            return None, f"""call math.clamp({args[0]}, {args[1]}, {args[2]}, {args[3]})
"""

        @predefined_function("math_clamp", [False, False, False], 1)
        def _fun_math_clamp(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.clamp({var_str}, [{args[0]}], [{args[1]}, {args[2]}])
"""

        @predefined_function("nf_math_rand", [True])
        def _math_rand(context, args):
            return None, f"""call math.rand({args[0]})
"""

        @predefined_function("math_rand", [], 1)
        def _fun_math_rand(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.rand({var_str})
"""

        @predefined_function("nf_math_sort", [True])
        def _math_sort(context, args):
            return None, f"""call math.sort({args[0]})
"""

        @predefined_function("nf_math_muldiv", [True, True, True, True])
        def _math_muldiv(context, args):
            return None, f"""call math.muldiv({args[0]}, {args[1]}, {args[2]}, {args[3]})
"""

        @predefined_function("math_muldiv", [False, False, False], 1)
        def _fun_math_muldiv(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.muldiv({var_str}, [{args[0]}], [{args[1]}, {args[2]}])
"""

        @predefined_function("nf_math_atan2", [True, True, True])
        def _math_atan2(context, args):
            return None, f"""call math.atan2({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("math_atan2", [False, False], 1)
        def _fun_math_atan2(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.atan2({var_str}, [{args[0]}], [{args[1]}])
"""

        @predefined_function("nf_math_sin", [True, True])
        def _math_sin(context, args):
            return None, f"""call math.sin({args[0]}, {args[1]})
"""

        @predefined_function("math_sin", [False], 1)
        def _fun_math_sin(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.sin({var_str}, [{args[0]}])
"""

        @predefined_function("nf_math_cos", [True, True])
        def _math_cos(context, args):
            return None, f"""call math.cos({args[0]}, {args[1]})
"""

        @predefined_function("math_cos", [False], 1)
        def _fun_math_cos(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.cos({var_str}, [{args[0]}])
"""

        @predefined_function("nf_math_rot2", [True, True, False])
        def _math_rot2(context, args):
            return None, f"""call math.rot2({args[0]}, {args[1]}, {args[2]})
"""

        @predefined_function("nf_math_sqrt", [True, True])
        def _math_sqrt(context, args):
            return None, f"""call math.sqrt({args[0]}, {args[1]})
"""

        @predefined_function("math_sqrt", [False], 1)
        def _fun_math_sqrt(context, args):
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

    @staticmethod
    def decode_attr(node):
        """Decode an attribute or name and convert it to a dotted name.
        """
        name = ""
        while isinstance(node, ast.Attribute):
            name = "." + node.attr + name
            node = node.value
        if isinstance(node, ast.Name):
            name = node.id + name
        else:
            raise TranspilerError("invalid name", ast_node=node)
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
                        raise TranspilerError(f"unsupported function decorator type {ast.dump(decorator)}", ast_node=node)
                    if decorator.id != "onevent":
                        raise TranspilerError(f'unsupported function decorator "{decorator.id}"', ast_node=node)
                    is_onevent = True
                if node.name in parent_context.functions:
                    raise TranspilerError(f"function {node.name} defined multiple times", ast_node=node)
                if len(node.args.args) > 0:
                    if is_onevent:
                        raise TranspilerError(f"unexpected arguments in @onevent function {node.name}", ast_node=node)
                    if len(node.args.defaults) > 0:
                        raise TranspilerError(f"unsupported default values for arguments of {node.name}", ast_node=node)
                    if len({a.arg for a in node.args.args}) < len(node.args.args):
                        raise TranspilerError(f"multiple arguments with the same name in function {node.name}", ast_node=node)
                if node.args.vararg is not None:
                    raise TranspilerError(f"unsupported varargs in arguments of {node.name}", ast_node=node)
                if node.args.kwarg is not None:
                    raise TranspilerError(f"unsupported kwargs in arguments of {node.name}", ast_node=node)
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
            }[type(node.op)]
            left, aux_st, _ = self.compile_expr(node.left, context, priority)
            aux_statements += aux_st
            right, aux_st, _ = self.compile_expr(node.right, context, priority)
            aux_statements += aux_st
            code = f"{left} {op_str} {right}"
        elif isinstance(node, ast.BoolOp):
            # with shortcuts, useful e.g. to avoid out-of-bound array indexing
            # result is not pretty b/c of aseba's idea of what's acceptable
            cmp = "!=" if isinstance(node.op, ast.And) else "=="
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
                    raise TranspilerError(f"too many arguments in call to function {fun_name}", ast_node=node)
                if len(node.args) < len(function_def.function_def.args.args):
                    raise TranspilerError(f"too few arguments in call to function {fun_name}", ast_node=node)
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
                        raise TranspilerError("function without return value called in an expression", ast_node=node)
                return code, aux_statements, False
            if fun_name in self.predefined_function_dict:
                predefined_function = self.predefined_function_dict[fun_name]
                if len(node.args) != len(predefined_function.argin):
                    raise TranspilerError(f"wrong number of arguments for function {fun_name}", ast_node=node)
                if predefined_function.nargout != 1:
                    raise TranspilerError(f"wrong number of results for function {fun_name}", ast_node=node)
                values, aux_statements = predefined_function.get_code(self, context, node.args)
                return values[0], aux_statements, False
            # hard-coded functions
            if fun_name == "abs":
                if len(node.args) != 1:
                    raise TranspilerError("wrong number of arguments for abs", ast_node=node)
                code, aux_st, is_boolean = self.compile_expr(node.args[0], context, self.PRI_COMMA)
                aux_statements += aux_st
                code = f"abs({code})"
                return code, aux_statements, False
            if fun_name == "len":
                if len(node.args) != 1:
                    raise TranspilerError("wrong number of arguments for len", ast_node=node)
                if isinstance(node.args[0], ast.Name):
                    len_arg_size = context.var_array_size(node.args[0].id)
                    code = f"{len_arg_size}" if len_arg_size is not None else "0"
                elif isinstance(node.args[0], ast.List):
                    code = f"{len(node.args[0].elts)}"
                else:
                    raise TranspilerError("type of argument of len is not a list", ast_node=node)
                return code, aux_statements, False
            raise TranspilerError(f"unknown function {fun_name}", ast_node=node)
        elif isinstance(node, ast.Compare):
            op_str = {
                ast.Eq: "==",
                ast.Gt: ">",
                ast.GtE: ">=",
                ast.Lt: "<",
                ast.LtE: "<=",
                ast.NotEq: "!=",
            }
            # quick check of operators
            for op in node.ops:
                if type(op) not in op_str:
                    raise TranspilerError(f"comparison op {ast.dump(op)} not implemented", ast_node=node)
            if len(node.ops) == 1:
                # one comparison: straighforward transpilation
                op = node.ops[0]
                priority = self.PRI_COMPARISON
                left, aux_st, _ = self.compile_expr(node.left, context, self.PRI_NUMERIC)
                aux_statements += aux_st
                right, aux_st, _ = self.compile_expr(node.comparators[0], context, self.PRI_NUMERIC)
                aux_statements += aux_st
                code = f"{left} {op_str[type(op)]} {right}"
                is_boolean = True
            else:
                # chained comparisons a op0 b0 op1 b1 ... ->
                # tmp_b = 0; tmp_l = a;
                # tmp_r = b0; if tmp_l op0 tmp_r then tmp_l = tmp_r
                # tmp_r = b1; if tmp_l op1 tmp_r then tmp_l = tmp_r
                # ...
                # tmp_r = b1; if tmp_l opn tmp_r then tmp_b = 1
                # end end ... end
                tmp_offset = context.request_tmp_expr(3)
                left, aux_st, _ = self.compile_expr(node.left, context, self.PRI_NUMERIC)
                aux_statements += aux_st
                aux_statements += f"""{context.tmp_var_str(tmp_offset)} = 0
{context.tmp_var_str(tmp_offset + 1)} = {left}
"""
                for i in range(len(node.ops)):
                    right, aux_st, _ = self.compile_expr(node.comparators[i], context, self.PRI_NUMERIC)
                    aux_statements += aux_st
                    aux_statements += f"""{context.tmp_var_str(tmp_offset + 2)} = {right}
if {context.tmp_var_str(tmp_offset + 1)} {op_str[type(node.ops[i])]} {context.tmp_var_str(tmp_offset + 2)} then
"""
                    if i + 1 < len(node.ops):
                        aux_statements += f"""{context.tmp_var_str(tmp_offset + 1)} = {context.tmp_var_str(tmp_offset + 2)}
"""
                aux_statements += f"""{context.tmp_var_str(tmp_offset)} = 1
"""
                for _ in node.ops:
                    aux_statements += """end
"""
                code = context.tmp_var_str(tmp_offset)
        elif isinstance(node, (ast.Constant, ast.NameConstant)):
            if node.value is False:
                code = "0"
            elif node.value is True:
                code = "1"
            else:
                raise TranspilerError(f"unsupported constant {node.value}", node)
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
        elif isinstance(node, ast.Index):
            code, aux_st, is_boolean = self.compile_expr(node.value, context, self.PRI_NUMERIC)
            aux_statements += aux_st
            return code, aux_statements, False
        elif isinstance(node, ast.List):
            if priority_container > self.PRI_ASSIGN:
                raise TranspilerError("list not supported in expression", node)
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
            var_array_size = context.var_array_size(node.id)
            if var_array_size is False:
                raise TranspilerError(f"unknown variable {node.id}", node)
            if isinstance(var_array_size, int):
                raise TranspilerError(f"list variable {node.id} used in expression", node)
            code = context.var_str(node.id)
        elif isinstance(node, ast.Subscript):
            name = self.decode_attr(node.value)
            var_array_size = context.var_array_size(name)
            if var_array_size is False:
                raise TranspilerError(f"unknown variable {name}", node)
            if var_array_size is None:
                raise TranspilerError(f"indexing of variable {name} which is not a list", node)
            index = node.slice
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
            code = f"{context.var_str(name)}[{index_value}]"
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
                raise TranspilerError(f"unsupported unary op {op}", node)
        else:
            raise TranspilerError(f"node {ast.dump(node)} not implemented", node)

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
        if priority < priority_container:
            return "(" + code + ")", aux_statements, is_boolean
        return code, aux_statements, is_boolean

    def decode_target(self, target):
        """Decode an assignment target and return variable name (possibly dotted) and
        index node (or None)
        """
        index = None
        if isinstance(target, ast.Subscript):
            index = target.slice
            target = target.value
        name = self.decode_attr(target)
        return name, index

    def compile_node(self, node, context):
        """Compile an ast statement node.
        """
        code = ""
        context.reset_tmp_req_current_expr()
        if isinstance(node, ast.Assign):
            # decide target
            if len(node.targets) != 1:
                raise TranspilerError("unsupported assignment to multiple targets", node)
            target, index = self.decode_target(node.targets[0])
            target_str = context.var_str(target)
            if index is None:
                # declare target
                if isinstance(node.value, ast.List):
                    # var = [...]
                    target_size = len(node.value.elts)
                    context.declare_var(target, target_size, ast_node=node)
                elif isinstance(node.value, (ast.Name, ast.Attribute)):
                    # var1 = var2: inherit size
                    name_right = self.decode_attr(node.value)
                    target_size = context.var_array_size(name_right)
                    if target_size is False:
                        raise TranspilerError(f"unknown variable {name_right}", node)
                    context.declare_var(target, target_size, ast_node=node)
                    # code special case (parsing of var2 as an expression would fail)
                    return f"""{target_str} = {context.var_str(name_right)}
"""
                else:
                    context.declare_var(target, ast_node=node)
            # compile value
            if isinstance(node.value, ast.List):
                if index is not None:
                    raise TranspilerError("list assigned to indexed variable", node)
                value, aux_statements, is_boolean = self.compile_expr(node.value, context, self.PRI_ASSIGN)
            else:
                value, aux_statements, is_boolean = self.compile_expr(node.value, context, self.PRI_NUMERIC)
            code += aux_statements
            # generate code, taking care of indexing and boolean conversion
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
                code += f"""{target_str} = {value}
"""
            return code
        if isinstance(node, ast.AugAssign):
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
        if isinstance(node, ast.Expr):
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
                        raise TranspilerError(f"wrong number of arguments for function {fun_name}", node)
                    _, aux_statements = predefined_function.get_code(self, context, expr.args)
                    return aux_statements
                if fun_name == "emit":
                    # hard-coded emit(name, params...)
                    if (len(expr.args) < 1 or
                        not isinstance(expr.args[0], ast.Constant) or
                        not isinstance(expr.args[0].value, str)):
                        raise TranspilerError("bad event name in emit", node)
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
        if isinstance(node, ast.For):
            # for var in range(...): ...
            if not isinstance(node.target, ast.Name):
                raise TranspilerError("for loop with unsupported target (not a plain variable)", node)
            if (not isinstance(node.iter, ast.Call) or
                not isinstance(node.iter.func, ast.Name) or
                node.iter.func.id != "range" or
                len(node.iter.args) < 1 or len(node.iter.args) > 3):
                raise TranspilerError("for loop with unsupported iterator (not range)", node)
            range_args = node.iter.args
            target = self.decode_attr(node.target)
            target_str = context.var_str(target)
            context.declare_var(target, ast_node=node)
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
        if isinstance(node, ast.Global):
            for name in node.names:
                context.declare_global(name, node)
            return ""
        if isinstance(node, ast.If):
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
        if isinstance(node, ast.Pass):
            return ""
        if isinstance(node, ast.Return):
            if context.parent_context is None:
                raise TranspilerError("return outside function", node)
            if context.is_onevent and node.value is not None:
                raise TranspilerError(f"returned value in @onevent function {context.function_name}", node)
            if context.has_return_val is None:
                context.has_return_val = node.value is not None
            elif context.has_return_val != (node.value is not None):
                raise TranspilerError(f"inconsistent return values in function {context.function_name}", node)
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
        if isinstance(node, ast.While):
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

        raise TranspilerError(f"node {ast.dump(node)} not implemented", node)

    def compile_node_array(self, node_array, context):
        """Compile an array of ast statement nodes.
        """
        code = "".join([
            self.compile_node(node, context)
            for node in node_array
        ])
        return code

    def transpile(self):
        """Transpile whole Python source code.
        """

        # top-level context
        context_top = Context()

        # parse and split into top code and function definitions
        try:
            self.ast = ast.parse(self.src)
        except SyntaxError as error:
            raise TranspilerError(error.args[0], syntax_error=error) from None
        top_code = self.split(context_top)

        # compile top-level code (first pass for global variable sizes)
        self.output_src = self.compile_node_array(top_code, context_top)

        # functions
        function_src = ""
        for fun_name in context_top.functions:
            # first pass to gather local variables into context_fun[.] (not declared global, but assigned to)
            # function return type isn't known yet (context.has_ret_value = None doesn't raise exceptions)
            _ = self.compile_node_array(context_top.functions[fun_name].function_def.body, context_top.functions[fun_name])
            # set functions without return statements to void
            context_top.functions[fun_name].freeze_return_type()
            # second pass to produce transpiled code with correct local variable names
            fun_output_src = self.compile_node_array(context_top.functions[fun_name].function_def.body, context_top.functions[fun_name])
            if context_top.functions[fun_name].is_onevent:
                function_src += f"""
onevent {fun_name.replace("_", ".")}
"""
            else:
                function_src += f"""
sub {fun_name}
"""
            function_src += fun_output_src

        # compile top-level code again, now that function return types are known
        self.output_src = self.compile_node_array(top_code, context_top) + function_src

        # check recursivity
        for fun_name in context_top.functions:
            if context_top.functions[fun_name].is_recursive(context_top.functions):
                raise TranspilerError(f"recursive function {fun_name}", context_top.functions[fun_name].function_def)

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

    @staticmethod
    def simple_transpile(input_src):
        transpiler = ATranspiler()
        transpiler.set_source(input_src)
        transpiler.transpile()
        output_src = transpiler.get_output()
        return output_src
