# Demo of exit() function

i = 0

timer_period[0] = 250
leds_cicle = 8 * [0]

@onevent
def timer0():
    global i, leds_circle
    leds_circle[i] = 32
    i += 1
    if i >= 8:
        exit()
