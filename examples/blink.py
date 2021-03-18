on = False

timer.period[0] = 500

@onevent
def timer0():
    on = not on
    if on:
        leds.top = [32, 32, 0]
    else:
        leds.top = [0, 0, 0]
