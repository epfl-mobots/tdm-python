on = False

timer.period[0] = 500

@onevent
def timer0():
    on = not on
    leds.top = [32 * on, 32 * on, 0]
