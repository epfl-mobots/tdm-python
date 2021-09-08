# Demo of print(...) function

i = 0

timer_period[0] = 1000

@onevent
def timer0():
    global i, leds_top
    i += 1
    is_odd = i % 2 == 1
    if is_odd:
        print(i, "odd")
        leds_top = [0, 32, 32]
    else:
        print(i, "even")
        leds_top = [0, 0, 0]

@onevent
def button_center():
    exit()
