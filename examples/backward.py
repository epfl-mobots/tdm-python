@onevent
def prox():
    prox_front = prox.horizontal[2]
    speed = -prox_front // 10
    motor.left.target = speed
    motor.right.target = speed

