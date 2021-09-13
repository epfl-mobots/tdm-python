i = 0
timer_period[0] = 200

@onevent
def timer0():
    global i, prox_horizontal
    i += 1
    if i > 20:
        exit()
    emit("front", prox_horizontal[2])
