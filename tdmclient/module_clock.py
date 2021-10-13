# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Clock module for transpiler
"""

from tdmclient.atranspiler import Module, AFunction

class ModuleClock(Module):

    def __init__(self, transpiler):
        super().__init__(transpiler, "Clock")

        @AFunction.define(self.functions, "ticks_50Hz", [], 1)
        def _ticks_50Hz(context, args):
            return ["_ticks50Hz"], ""

        @AFunction.define(self.functions, "seconds", [], 1)
        def _seconds(context, args):
            return ["(_ticks50Hz / 50)"], ""

        @AFunction.define(self.functions, "reset", [])
        def _reset(context, args):
            return None, f"""_ticks50Hz = 0
"""

    def on_import(self):
        self.transpiler.add_onevent_preamble("buttons",
                                             "_ticks50Hz++\n",
                                             {"_ticks50Hz": 0})
