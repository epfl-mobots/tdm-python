# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Thymio module for transpiler
"""

from tdmclient.atranspiler import Module, AFunction

class ModuleThymio(Module):

    def __init__(self):
        super().__init__("Thymio")
        self.constants = {
            "BLACK": ("[0, 0, 0]", 3),
            "BLUE": ("[0, 0, 32]", 3),
            "CYAN": ("[0, 32, 32]", 3),
            "GREEN": ("[0, 32, 0]", 3),
            "MAGENTA": ("[32, 0, 32]", 3),
            "RED": ("[32, 0, 0]", 3),
            "WHITE": ("[32, 32, 32]", 3),
            "YELLOW": ("[32, 32, 0]", 3),
        }
        self.variables = {
            "acc": ("acc", 3),
            "button_backward": ("button.backward", None),
            "button_center": ("button.center", None),
            "button_forward": ("button.forward", None),
            "button_left": ("button.left", None),
            "button_right": ("button.right", None),
            "events_arg": ("events.arg", 32),
            "events_source": ("events.source", None),
            "leds_bottom_left": ("leds.bottom.left", 3),
            "leds_bottom_right": ("leds.bottom.right", 3),
            "leds_circle": ("leds.circle", 8),
            "leds_top": ("leds.top", 3),
            "mic_intensity": ("mic.intensity", None),
            "mic_threshold": ("mic.threshold", None),
            "motor_left_pwm": ("motor.left.pwm", None),
            "motor_left_speed": ("motor.left.speed", None),
            "motor_left_target": ("motor.left.target", None),
            "motor_right_pwm": ("motor.right.pwm", None),
            "motor_right_speed": ("motor.right.speed", None),
            "motor_right_target": ("motor.right.target", None),
            "prox_comm_rx": ("prox.comm.rx", None),
            "prox_comm_tx": ("prox.comm.tx", None),
            "prox_ground_ambient": ("prox.ground.ambient", 2),
            "prox_ground_delta": ("prox.ground.delta", 2),
            "prox_ground_reflected": ("prox.ground.reflected", 2),
            "prox_horizontal": ("prox.horizontal", 7),
            "rc5_address": ("rc5.address", None),
            "rc5_command": ("rc5.command", None),
            "sd_present": ("sd.present", None),
            "temperature": ("temperature", None),
            "timer_period": ("timer.period", 2),
        }

        @AFunction.define(self.functions, "nf_math_copy", [True, True])
        def _math_copy(context, args):
            return None, f"""call math.copy({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "nf_math_fill", [True, False])
        def _math_fill(context, args):
            return None, f"""call math.fill({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "nf_math_addscalar", [True, True, False])
        def _math_addscalar(context, args):
            return None, f"""call math.addscalar({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_math_add", [True, True, True])
        def _math_add(context, args):
            return None, f"""call math.add({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_math_sub", [True, True, True])
        def _math_sub(context, args):
            return None, f"""call math.sub({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_math_mul", [True, True, True])
        def _math_mul(context, args):
            return None, f"""call math.mul({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_math_div", [True, True, True])
        def _math_div(context, args):
            return None, f"""call math.div({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_math_min", [True, True, True])
        def _math_min(context, args):
            return None, f"""call math.min({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "math_min", [False, False], 1)
        def _fun_math_min(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.min({var_str}, [{args[0]}], [{args[1]}])
"""

        @AFunction.define(self.functions, "nf_math_max", [True, True, True])
        def _math_max(context, args):
            return None, f"""call math.max({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "math_max", [False, False], 1)
        def _fun_math_max(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.max({var_str}, [{args[0]}], [{args[1]}])
"""

        @AFunction.define(self.functions, "nf_math_clamp", [True, True, True, True])
        def _math_clamp(context, args):
            return None, f"""call math.clamp({args[0]}, {args[1]}, {args[2]}, {args[3]})
"""

        @AFunction.define(self.functions, "math_clamp", [False, False, False], 1)
        def _fun_math_clamp(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.clamp({var_str}, [{args[0]}], [{args[1]}], [{args[2]}])
"""

        @AFunction.define(self.functions, "nf_math_rand", [True])
        def _math_rand(context, args):
            return None, f"""call math.rand({args[0]})
"""

        @AFunction.define(self.functions, "math_rand", [], 1)
        def _fun_math_rand(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.rand({var_str})
"""

        @AFunction.define(self.functions, "nf_math_sort", [True])
        def _math_sort(context, args):
            return None, f"""call math.sort({args[0]})
"""

        @AFunction.define(self.functions, "nf_math_muldiv", [True, True, True, True])
        def _math_muldiv(context, args):
            return None, f"""call math.muldiv({args[0]}, {args[1]}, {args[2]}, {args[3]})
"""

        @AFunction.define(self.functions, "math_muldiv", [False, False, False], 1)
        def _fun_math_muldiv(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.muldiv({var_str}, [{args[0]}], [{args[1]}], [{args[2]}])
"""

        @AFunction.define(self.functions, "nf_math_atan2", [True, True, True])
        def _math_atan2(context, args):
            return None, f"""call math.atan2({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "math_atan2", [False, False], 1)
        def _fun_math_atan2(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.atan2({var_str}, [{args[0]}], [{args[1]}])
"""

        @AFunction.define(self.functions, "nf_math_sin", [True, True])
        def _math_sin(context, args):
            return None, f"""call math.sin({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "math_sin", [False], 1)
        def _fun_math_sin(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.sin({var_str}, [{args[0]}])
"""

        @AFunction.define(self.functions, "nf_math_cos", [True, True])
        def _math_cos(context, args):
            return None, f"""call math.cos({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "math_cos", [False], 1)
        def _fun_math_cos(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.cos({var_str}, [{args[0]}])
"""

        @AFunction.define(self.functions, "nf_math_rot2", [True, True, False])
        def _math_rot2(context, args):
            return None, f"""call math.rot2({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_math_sqrt", [True, True])
        def _math_sqrt(context, args):
            return None, f"""call math.sqrt({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "math_sqrt", [False], 1)
        def _fun_math_sqrt(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call math.sqrt({var_str}, [{args[0]}])
"""

        @AFunction.define(self.functions, "nf__leds_set", [False, False])
        def _leds_set(context, args):
            return None, f"""call _leds.set({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "nf__system_reboot", [])
        def _system_reboot(context, args):
            return None, """call _system.reboot()
"""

        @AFunction.define(self.functions, "nf__system_settings_read", [False], 1)
        def _fun__system_settings_read(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call _system.settings.read({args[0]}, {var_str})
"""

        @AFunction.define(self.functions, "nf__system_settings_write", [False, False])
        def _system_settings_write(context, args):
            return None, f"""call _system.settings.write({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "nf__poweroff", [])
        def _poweroff(context, args):
            return None, """call _poweroff()
"""

        # functions defined in thymio_natives.c

        @AFunction.define(self.functions, "nf__leds_set", [False, False])
        def _leds_set(context, args):
            return None, f"""call _leds.set({args[0]}, {args[1]})

"""

        @AFunction.define(self.functions, "nf_sound_record", [False])
        def _sound_record(context, args):
            return None, f"""call sound.record({args[0]})
"""

        @AFunction.define(self.functions, "nf_sound_play", [False])
        def _sound_play(context, args):
            return None, f"""call sound.play({args[0]})
"""

        @AFunction.define(self.functions, "nf_sound_replay", [False])
        def _sound_replay(context, args):
            return None, f"""call sound.replay({args[0]})
"""

        @AFunction.define(self.functions, "nf_sound_duration", [False], 1)
        def _sound_duration(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call sound.duration({args[0]}, {var_str})
"""

        @AFunction.define(self.functions, "nf_sound_system", [False])
        def _sound_system(context, args):
            return None, f"""call sound.system({args[0]})
"""

        @AFunction.define(self.functions, "nf_leds_circle", [False, False, False, False, False, False, False, False])
        def _leds_circle(context, args):
            return None, f"""call leds.circle({args[0]}, {args[1]}, {args[2]}, {args[3]}, {args[4]}, {args[5]}, {args[6]}, {args[7]})
"""

        @AFunction.define(self.functions, "nf_leds_top", [False, False, False])
        def _leds_top(context, args):
            return None, f"""call leds.top({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_leds_bottom_right", [False, False, False])
        def _leds_bottom_right(context, args):
            return None, f"""call leds.bottom.right({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_leds_bottom_left", [False, False, False])
        def _leds_bottom_left(context, args):
            return None, f"""call leds.bottom.left({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "nf_leds_buttons", [False, False, False, False])
        def _leds_buttons(context, args):
            return None, f"""call leds.buttons({args[0]}, {args[1]}, {args[2]}, {args[3]})
"""

        @AFunction.define(self.functions, "nf_leds_prox_h", [False, False, False, False, False, False, False, False])
        def _leds_prox_h(context, args):
            return None, f"""call leds.prox.h({args[0]}, {args[1]}, {args[2]}, {args[3]}, {args[4]}, {args[5]}, {args[6]}, {args[7]})
"""

        @AFunction.define(self.functions, "nf_leds_prox_v", [False, False])
        def _leds_prox_v(context, args):
            return None, f"""call leds.prox.v({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "nf_leds_rc", [False])
        def _leds_rc(context, args):
            return None, f"""call leds.rc({args[0]})
"""

        @AFunction.define(self.functions, "nf_leds_sound", [False])
        def _leds_sound(context, args):
            return None, f"""call leds.sound({args[0]})
"""

        @AFunction.define(self.functions, "nf_leds_temperature", [False, False])
        def _leds_temperature(context, args):
            return None, f"""call leds.temperature({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "nf_sound_freq", [False, False])
        def _sound_freq(context, args):
            return None, f"""call sound.freq({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "nf_sound_wave", [True])
        def _sound_wave(context, args):
            return None, f"""call sound.wave({args[0]})
"""

        @AFunction.define(self.functions, "nf_prox_comm_enable", [False])
        def _prox_comm_enable(context, args):
            return None, f"""call prox.comm.enable({args[0]})
"""

        @AFunction.define(self.functions, "nf_sd_open", [False], 1)
        def _fun_sd_open(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call sd.open({args[0]}, {var_str})
"""

        @AFunction.define(self.functions, "nf_sd_write", [True], 1)
        def _fun_sd_write(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call sd.write({args[0]}, {var_str})
"""

        @AFunction.define(self.functions, "nf_sd_read", [True], 1)
        def _fun_sd_read(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call sd.read({args[0]}, {var_str})
"""

        @AFunction.define(self.functions, "nf_sd_seek", [False], 1)
        def _fun_sd_seek(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call sd.seek({args[0]}, {var_str})
"""

        # @AFunction.define(self.functions, "nf__rf_nodeid", [False])
        # def _rf_nodeid(context, args):
        #     return None, f"call _rf.nodeid({args[0]})\n"

        # @AFunction.define(self.functions, "nf__rf_setupd", [False, False])
        # def _rf_setup(context, args):
        #     return None, f"call _rf.setup({args[0]}, {args[1]})\n"

        @AFunction.define(self.functions, "deque_size", [True], 1)
        def _deque_size(context, args):
            tmp_offset = context.request_tmp_expr()
            var_str = context.tmp_var_str(tmp_offset)
            return [var_str], f"""call deque.size({args[0]}, {var_str})
"""

        @AFunction.define(self.functions, "deque_push_front", [True, True])
        def _deque_push_front(context, args):
            return None, f"""call deque.push_front({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "deque_push_back", [True, True])
        def _deque_push_back(context, args):
            return None, f"""call deque.push_back({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "deque_pop_front", [True, True])
        def _deque_pop_front(context, args):
            return None, f"""call deque.pop_front({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "deque_pop_back", [True, True])
        def _deque_pop_back(context, args):
            return None, f"""call deque.pop_back({args[0]}, {args[1]})
"""

        @AFunction.define(self.functions, "deque_get", [True, True, False])
        def _deque_get(context, args):
            return None, f"""call deque.get({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "deque_set", [True, True, False])
        def _deque_set(context, args):
            return None, f"""call deque.set({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "deque_insert", [True, True, False])
        def _deque_insert(context, args):
            return None, f"""call deque.insert({args[0]}, {args[1]}, {args[2]})
"""

        @AFunction.define(self.functions, "deque_erase", [True, False, False])
        def _deque_erase(context, args):
            return None, f"""call deque.erase({args[0]}, {args[1]}, {args[2]})
"""
