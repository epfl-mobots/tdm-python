import clock

@onevent
def button_left():
    print("clock.seconds()", clock.seconds())

@onevent
def button_right():
    print("clock.ticks_50Hz()", clock.ticks_50Hz())

@onevent
def button_backward():
    print("clock.reset()")
    clock.reset()

@onevent
def button_center():
    exit()
