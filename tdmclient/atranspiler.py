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

        # dict module_name: module (import module_name)
        self.modules = {}
        # dict symbol_asname: (module, symbol_name) (from module_name import symbol_name as symbol_asname)
        self.module_symbols = {}

    def is_global(self, name):
        """Check if a variable is global or not.
        """
        return name not in self.var

    def var_str(self, name, is_target=False):
        """Convert a variable name to its string representation in output
        source code.
        """
        is_global = self.is_global(name)
        context = self.parent_context if is_global and self.parent_context is not None else self
        module_value = context.get_module_value(name, not is_target)
        if module_value:
            return module_value
        if self.function_name is None or is_global:
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

    def add_module(self, module_name, module, symbols=None):
        if symbols is None:
            self.modules[module_name] = module
        else:
            for symbol in symbols:
                self.module_symbols[symbol] = module, symbols[symbol]

    def declare_global(self, name, ast_node=None):
        """Declare a global variable.
        """
        if name in self.var:
            raise TranspilerError(f"variable '{name}' declared global after being assigned to", ast_node)
        self.global_var.add(name)

    def declare_var(self, name, size=None, ast_node=None):
        """Declare a variable with its size (array size, or None if scalar).
        """
        context = self.parent_context if name in self.global_var and self.parent_context is not None else self
        if "." not in name and context.get_module_for_symbol(name) is None:
            if name in context.var:
                if (size != context.var[name] or
                    name in self.global_var and name in ATranspiler.PREDEFINED_VARIABLES and size != ATranspiler.PREDEFINED_VARIABLES[name]):
                    raise TranspilerError(f"incompatible sizes for list assignment to '{name}'", ast_node)
            else:
                context.var[name] = size

    def get_module_value(self, name, ancestors=False):
        """Get the value of a variable or constant defined in an imported module.
        """
        if "." in name:
            module_name, name = name.split(".", 1)
            module = self.get_module(module_name)
        else:
            module_and_name = self.get_module_for_symbol(name, ancestors)
            if module_and_name is None:
                return None
            module, name = module_and_name
        return module.constants[name][0] if name in module.constants else module.variables[name][0] if name in module.variables else None

    def get_module_function(self, name):
        """Get a function defined in an imported module.
        """
        if "." in name:
            module_name, name = name.split(".", 1)
            module = self.get_module(module_name)
        else:
            module_and_name = self.get_module_for_symbol(name, True)
            if module_and_name is None:
                return None
            module, name = module_and_name
        return module.functions[name] if name in module.functions else None

    def get_module(self, module_name):
        """Return module in current context or ancestor.
        """
        if module_name in self.modules:
            return self.modules[module_name]
        elif self.parent_context is not None:
            return self.parent_context.get_module(module_name)
        else:
            raise NameError(f"name '{module_name}' is not defined")

    def get_module_for_symbol(self, symbol, ancestors=False):
        """Return module and name where symbol is defined in current context, and
        optionally also in ancestors.
        """
        return (self.module_symbols[symbol] if symbol in self.module_symbols
                else self.parent_context.get_module_for_symbol(symbol, True) if ancestors and self.parent_context is not None
                else None)

    def var_array_size(self, name):
        """Return size if name is a local or global array variable,
        None if it is a local or global scalar, or False if unknown.
        """
        if "." in name:
            module_name, name = name.split(".", 1)
            module = self.get_module(module_name)
            return (module.constants[name][1] if name in module.constants
                    else module.variables[name][1] if name in module.variables
                    else False)
        else:
            module_and_name = self.get_module_for_symbol(name, True)
            if module_and_name is not None:
                module, name = module_and_name
                return (module.constants[name][1] if name in module.constants
                    else module.variables[name][1] if name in module.variables
                    else False)
            var = (ATranspiler.PREDEFINED_VARIABLES if name in ATranspiler.PREDEFINED_VARIABLES
                else self.parent_context.var if name in self.global_var and self.parent_context is not None
                else self.var)
            return False if name not in var else var[name]

    def var_declarations(self):
        """Output source code for local variable declarations.
        """
        return "".join([
            f"var {self.var_str(name, True)}{f'[{self.var[name]}]' if self.var[name] is not None else ''}\n"
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
                    if fun == self.function_name or connect(fun):
                        return True
                    connections_upd |= connections[fun]
                connections[fun_name] = connections_upd
            return False

        for fun_name in self.called_functions:
            if connect(fun_name):
                return fun_name

        return None


class AFunction:
    """Transpilation information for aseba functions.
    """

    @staticmethod
    def define(dict, name, argin, nargout=0):
        """Decorator to add aseba function definition to a dictionary.
        """

        def register(fun):
            dict[name] = AFunction(name, argin, nargout, fun)
            return fun

        return register

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
        for i, arg in enumerate(args):
            if self.argin[i]:
                if isinstance(arg, ast.Name):
                    arg_code.append(arg.id)
                elif isinstance(arg, ast.List):
                    value, aux_st, _ = atranspiler.compile_expr(arg, context, atranspiler.PRI_ASSIGN)
                    aux_statements += aux_st
                    arg_code.append(value)
                else:
                    raise TranspilerError(f"list variable argument expected by function '{self.name}'",
                                          ast_node=arg)
            else:
                value, aux_st, _ = atranspiler.compile_expr(arg, context, ATranspiler.PRI_NUMERIC)
                aux_statements += aux_st
                arg_code.append(value)
        values, aux_st = self.fun(context, arg_code)
        aux_statements += aux_st
        return values, aux_statements


class Module:
    """Module known to transpiler.
    """

    def __init__(self, name, constants=None, variables=None, functions=None):
        self.name = name
        self.constants = constants or {}
        self.variables = variables or {}
        self.functions = functions or {}


class ATranspiler:
    """Transpiler from a subset of Python3 to Aseba.
    """

    # dict of Aseba variables mapped to python (empty, moved to thymio module)
    # var_name: var_array_size (number or None for scalar)
    PREDEFINED_VARIABLES = {
    }

    # set of built-in functions
    PREDEFINED_FUNCTIONS = {
        "emit",
        "exit",
        "print",
    }

    def __init__(self):
        self.preamble = None
        self.src = None
        self.ast_preamble = None
        self.ast = None
        self.output_src = None

        # fun_name: AFunction (empty, moved to thymio module)
        self.predefined_function_dict = {}

        # dict module_name: module (modules which can be imported)
        self.modules = {}

    def set_preamble(self, preamble):
        """Set the Python source code compiled just before source
        (typically import statements).
        """
        self.preamble = preamble

    def set_source(self, source):
        """Set the Python source code and reset transpilation.
        """
        self.src = source
        self.ast = None
        self.output_src = None
        self.print_format_strings = {}
        self.print_format_string_next_id = 0
        self.print_max_num_args = 0
        self.has_exit_event = False
        self.events = {}

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
        nodes = self.ast_preamble.body + self.ast.body if self.ast_preamble is not None else self.ast.body
        for node in nodes:
            if isinstance(node, ast.FunctionDef):
                is_onevent = False
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Name):
                        raise TranspilerError(f"unsupported function decorator type {ast.dump(decorator)}", ast_node=node)
                    if decorator.id != "onevent":
                        raise TranspilerError(f'unsupported function decorator "{decorator.id}"', ast_node=node)
                    is_onevent = True
                if node.name in parent_context.functions:
                    raise TranspilerError(f"function '{node.name}' defined multiple times", ast_node=node)
                if len(node.args.args) > 0:
                    if is_onevent:
                        raise TranspilerError(f"unexpected arguments in @onevent function '{node.name}'", ast_node=node)
                    if len(node.args.defaults) > 0:
                        raise TranspilerError(f"unsupported default values for arguments of '{node.name}'", ast_node=node)
                    if len({a.arg for a in node.args.args}) < len(node.args.args):
                        raise TranspilerError(f"multiple arguments with the same name in function '{node.name}'", ast_node=node)
                if node.args.vararg is not None:
                    raise TranspilerError(f"unsupported varargs in arguments of '{node.name}'", ast_node=node)
                if node.args.kwarg is not None:
                    raise TranspilerError(f"unsupported kwargs in arguments of '{node.name}'", ast_node=node)
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

    def reset_transpile_phase(self, next_id=0):
        self.print_format_strings = {}
        self.print_format_string_next_id = next_id

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
                # store value into _tmp[tmp_offset]
                aux_statements += aux_st
                if is_value_boolean:
                    aux_statements += f"""if {value} then
{context.tmp_var_str(tmp_offset)} = 1
else
{context.tmp_var_str(tmp_offset)} = 0
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
                    raise TranspilerError(f"too many arguments in call to function '{fun_name}'", ast_node=node)
                if len(node.args) < len(function_def.function_def.args.args):
                    raise TranspilerError(f"too few arguments in call to function '{fun_name}'", ast_node=node)
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
            a_function = context.get_module_function(fun_name)
            if a_function is None and fun_name in self.predefined_function_dict:
                a_function = self.predefined_function_dict[fun_name]
            if a_function is not None:
                if len(node.args) != len(a_function.argin):
                    raise TranspilerError(f"wrong number of arguments for function '{fun_name}'", ast_node=node)
                values, aux_statements = a_function.get_code(self, context, node.args)
                if a_function.nargout == 1:
                    code = values[0]
                else:
                    # no return value: must not be called in a subexpression
                    if priority_container != self.PRI_EXPR:
                        raise TranspilerError(f"wrong number of results for function '{fun_name}'", ast_node=node)
                return code, aux_statements, False
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
            raise TranspilerError(f"unknown function '{fun_name}'", ast_node=node)
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
                raise TranspilerError(f"unsupported constant '{node.value}'", node)
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
                raise TranspilerError(f"unknown variable '{node.id}'", node)
            if isinstance(var_array_size, int):
                raise TranspilerError(f"list variable '{node.id}' used in expression", node)
            code = context.var_str(node.id)
        elif isinstance(node, ast.Subscript):
            name = self.decode_attr(node.value)
            var_array_size = context.var_array_size(name)
            if var_array_size is False:
                raise TranspilerError(f"unknown variable '{name}'", node)
            if var_array_size is None:
                raise TranspilerError(f"indexing of variable '{name}' which is not a list", node)
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
                raise TranspilerError(f"unsupported unary op '{op}'", node)
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
            target_str = context.var_str(target, True)
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
                        raise TranspilerError(f"unknown variable '{name_right}'", node)
                    context.declare_var(target, target_size, ast_node=node)
                    # code special case (parsing of var2 as an expression would fail)
                    module_value = context.get_module_value(name_right, True)
                    if module_value:
                        return f"""{target_str} = {module_value}
"""
                    else:
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
                target_str += "[" + index_value + "]"
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
                        raise TranspilerError(f"wrong number of arguments for function '{fun_name}'", node)
                    _, aux_statements = predefined_function.get_code(self, context, expr.args)
                    return aux_statements
                if fun_name == "emit":
                    # hard-coded emit(name, params...) -> "emit name [params]"
                    if (len(expr.args) < 1 or
                        not isinstance(expr.args[0], ast.Constant) or
                        not isinstance(expr.args[0].value, str)):
                        raise TranspilerError("bad event name in emit", node)
                    event_name = expr.args[0].value
                    event_size = len(expr.args) - 1
                    if event_name in self.events:
                        if event_size != self.events[event_name]:
                            raise TranspilerError(f"inconsistent size for event '{event_name}'", node)
                    else:
                        self.events[event_name] = event_size
                    code = f"emit {event_name}"
                    aux_statements = ""
                    if len(expr.args) > 1:
                        for i in range(event_size):
                            value, aux_st, _ = self.compile_expr(expr.args[1 + i], context, self.PRI_NUMERIC)
                            aux_statements += aux_st
                            code += " [" if i == 0 else ", "
                            code += value
                        code += "]"
                    code = aux_statements + code + "\n"
                    return code
                elif fun_name == "exit":
                    # hard-coded exit(status=0) -> "emit _exit status"
                    if len(expr.args) > 1:
                        raise TranspilerError("too many arguments in exit", node)
                    if len(expr.args) == 1:
                        value, aux_st, _ = self.compile_expr(expr.args[0], context, self.PRI_NUMERIC)
                        code = aux_st + f"emit _exit {value}\n"
                    else:
                        code = "emit _exit 0\n"
                    self.has_exit_event = True
                    return code
                elif fun_name == "print":
                    # hard-coded print(args...) -> "emit _print [print_id, non_string_args...]"
                    print_format_string = ""
                    code = f"emit _print [{self.print_format_string_next_id}"
                    arg_count = 0
                    aux_statements = ""
                    for i, arg in enumerate(expr.args):
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            print_format_string += (" " if i > 0 else "") + arg.value
                        else:
                            value, aux_st, _ = self.compile_expr(arg, context, self.PRI_NUMERIC)
                            aux_statements += aux_st
                            code += ", " + value
                            arg_count += 1
                            print_format_string += " %d" if i > 0 else "%d"
                    code += ", 0" * (self.print_max_num_args - arg_count)
                    code += "]\n"
                    self.print_format_strings[self.print_format_string_next_id] = (print_format_string, arg_count)
                    self.print_format_string_next_id += 1
                    self.print_max_num_args = max(self.print_max_num_args, arg_count)
                    code = aux_statements + code
                    return code
            # parse expression, ignoring result
            _, aux_statements, _ = self.compile_expr(expr, context, self.PRI_EXPR)
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
                # stores limit a in _tmp[tmp_offset]
                tmp_offset = context.request_tmp_expr()
                value, aux_statements, is_boolean = self.compile_expr(range_args[0], context, self.PRI_NUMERIC)
                code += aux_statements
                code += f"""{target_str} = 0
{context.tmp_var_str(tmp_offset)} = {value}
while {target_str} < {context.tmp_var_str(tmp_offset)} do
"""
            elif len(range_args) == 2:
                # for var in range(a, b)
                # stores limit b in _tmp[tmp_offset]
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
                # stores limit b in _tmp[tmp_offset] and step c in _tmp[tmp_offset+1]
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
while {target_str} * {context.tmp_var_str(tmp_offset + 1)} < {context.tmp_var_str(tmp_offset)} * {context.tmp_var_str(tmp_offset + 1)} do
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
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                if module_name not in self.modules:
                    raise TranspilerError(f"unknown module '{module_name}'", node)
                context.add_module(alias.asname or module_name, self.modules[module_name])
            return ""
        if isinstance(node, ast.ImportFrom):
            module_name = node.module
            if module_name not in self.modules:
                raise TranspilerError(f"unknown module '{module_name}'", node)
            if len(node.names) == 1 and node.names[0].name == "*":
                # import all symbols
                context.add_module(module_name, self.modules[module_name],
                                   {
                                       name: name
                                       for name in {
                                           **self.modules[module_name].constants,
                                           **self.modules[module_name].variables,
                                           **self.modules[module_name].functions,
                                       }
                                   })
            else:
                context.add_module(module_name, self.modules[module_name],
                                {
                                    alias.asname or alias.name: alias.name
                                    for alias in node.names
                                })
            return ""
        if isinstance(node, ast.Pass):
            return ""
        if isinstance(node, ast.Return):
            if context.parent_context is None:
                raise TranspilerError("return outside function", node)
            if context.is_onevent and node.value is not None:
                raise TranspilerError(f"returned value in @onevent function '{context.function_name}'", node)
            if context.has_return_val is None:
                context.has_return_val = node.value is not None
            elif context.has_return_val != (node.value is not None):
                raise TranspilerError(f"inconsistent return values in function '{context.function_name}'", node)
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
            self.ast_preamble = ast.parse(self.preamble) if self.preamble is not None else None
            self.ast = ast.parse(self.src)
        except SyntaxError as error:
            raise TranspilerError(error.args[0], syntax_error=error) from None
        top_code = self.split(context_top)

        # compile top-level code (first pass for global variable sizes)
        self.reset_transpile_phase()
        self.output_src = self.compile_node_array(top_code, context_top)

        # reset for next phase
        self.reset_transpile_phase()

        # functions
        function_src = ""
        # first pass to gather local variables into context_fun[.] (not declared global, but assigned to)
        # function return type isn't known yet (context.has_ret_value = None doesn't raise exceptions)
        for fun_name in context_top.functions:
            fun_print_format_string_next_id = self.print_format_string_next_id
            _ = self.compile_node_array(context_top.functions[fun_name].function_def.body, context_top.functions[fun_name])
            # set functions without return statements to void
            context_top.functions[fun_name].freeze_return_type()
            self.reset_transpile_phase(fun_print_format_string_next_id)
        # second pass to produce transpiled code with correct local variable names
        for fun_name in context_top.functions:
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
                raise TranspilerError(f"recursive function '{fun_name}'", context_top.functions[fun_name].function_def)

        # variable declarations
        var_decl = context_top.var_declarations()
        var_decl += "".join([
            context_top.functions[fun_name].var_declarations()
            for fun_name in context_top.functions
        ])
        if len(var_decl) > 0:
            self.output_src = var_decl + "\n" + self.output_src

    def get_print_statements(self):
        """Get the python source code of a list of print statements
        where each element is a tuple with a format string and the number of numeric
        arguments, or None for no print statement.
        """
        return "[\n" + "\n".join([
            f"({repr(self.print_format_strings[id][0])}, {self.print_format_strings[id][1]}),"
            for id in sorted(self.print_format_strings)
        ]) + "\n]" if len(self.print_format_strings) > 0 else None

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
    def simple_transpile(input_src, modules=None, preamble=None):
        """Transpile program from python to aseba, returning the aseba source code.
        """
        transpiler = ATranspiler()
        if modules is not None:
            transpiler.modules = {**transpiler.modules, **modules}
        if preamble is not None:
            transpiler.set_preamble(preamble)
        transpiler.set_source(input_src)
        transpiler.transpile()
        output_src = transpiler.get_output()
        return output_src
