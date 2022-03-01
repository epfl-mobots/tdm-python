# This file is part of tdmclient.
# Copyright 2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Warnings for ATranspiler
"""

from tdmclient.atranspiler import ATranspiler


def missing_global_decl(transpiler):
    """Check if local variables have the same name as top-level variables.
    """

    r = {}
    for fun_name in transpiler.context_top.functions:
        undecl_var_set = set()
        fun = transpiler.context_top.functions[fun_name]
        for var_name in fun.var:
            if var_name != "_tmp":
                module_and_name = fun.get_module_for_symbol(var_name, True)
                if module_and_name is not None:
                    module, name = module_and_name
                    hidden = name in module.constants or name in module.variables
                else:
                    hidden = var_name in ATranspiler.PREDEFINED_VARIABLES or var_name in fun.parent_context.var
                if hidden:
                    undecl_var_set.add(var_name)
        if len(undecl_var_set) > 0:
            r[fun_name] = undecl_var_set

    return r
