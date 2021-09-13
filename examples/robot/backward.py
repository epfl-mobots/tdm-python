@onevent
def prox():
    global prox_horizontal, motor_left_target, motor_right_target
    prox_front = prox_horizontal[2]
    speed = -prox_front // 10
    motor_left_target = speed
    motor_right_target = speed
