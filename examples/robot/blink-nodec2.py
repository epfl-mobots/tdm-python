# blinking top led, same as blink.py but without function decorator

on = False

timer_period[0] = 500

def toggle_led():
    global on, leds_top
    on = not on
    if on:
        leds_top = [32, 32, 0]
    else:
        leds_top = [0, 0, 0]

onevent(toggle_led, "timer0")
