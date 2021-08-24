# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Thymio module for transpiler
"""

from tdmclient.atranspiler import Module

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
