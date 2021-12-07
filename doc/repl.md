
## Python repl for Thymio

The easiest way to explore the Thymio from Python is to use a special version of the Python _repl_ customized so that you're almost on the robot. A repl is a read-eval-print loop, i.e. the interactive environment where you type some code fragment (an expression, an assignment, a function call, or a longer piece of program), you hit the Return key and Python will evaluate your code, print the result and wait for more input.

To start the TDM repl, make sure that Thymio Suite is running and that a Thymio is connected. Then type the following command in your shell:
```
python3 -m tdmclient.tools.repl
```

A connection with the TDM will be established, the first robot will be found and locked, a message will be displayed to confirm that everything is fine, and you'll get the familiar Python prompt:
```
TDM:      192.168.1.20:57785
Robot:    AA003
Robot ID: 36d6627a-d1af-9571-9458-d9192d951664

>>>
```

Everything will work as expected: you can evaluate expressions, assign values to variables, create objects, define functions and classes, import modules and packages, open files on your hard disk to read or write to them, connect to the Internet... There are just two differences:
- Every time you type a command, the repl will check if your variables are known to the Thymio. Those whose name matches are synchronized with the Thymio before being used in expressions or after being assigned to. Python names are the same as Thymio name as they appear in the documentation and in Aseba Studio, except that dots are replaced with underscores (`leds.top` on the Thymio becomes `leds_top` in the repl). And the source code of function definitions will be remembered in case we need it later.
- A few functions specific to the Thymio are defined.

Here are a few examples of what you can do. Check that you can still use all the functions of Python:
```
>>> 1 + 2
3
>>> import math
>>> 2.3 * math.sin(3)
0.3245760185376946
>>>
```

Change the color of the RGB led on the top of the Thymio:
```
>>> leds_top = [0, 0, 32]
>>>
```

Get the Thymio temperature and convert it from tenths of degree Celsius to Kelvin. Notice we've waited a little too long between the two commands: the temperature has changed, or maybe the sensor measurement is corrupted by noise.
```
>>> temperature
281
>>> temp_K = temperature / 10 + 273.15
>>> temp_K
301.65
>>>
```

The function `sleep(t)`, specific to the TDM repl, waits for `t` seconds. The argument `t` is expressed in seconds and can be fractional and less than 1. The next code example stores 10 samples of the front proximity sensor, acquired with a sampling period of 0.5. We brought a hand close to the front of the robot twice during the 5 seconds the loop lasted.
```
>>> p = []
>>> for i in range(10):
...     p.append(prox_horizontal[2])
...     sleep(0.5)
...
>>> p
[0, 0, 0, 0, 2639, 3440, 0, 1273, 2974, 4444]
>>>
```

The code above runs on the computer, not on the Thymio. This is fine as long as the communication is fast enough for our needs. If you want to scan a barcode with the ground sensor by moving over it, depending on the robot speed, the sampling rate must be higher than what's allowed by the variable synchronization, especially between the TDM and the Thymio if you have a wireless dongle.

It's also possible to run code on the Thymio. You can define functions with the function decorator `@onevent` to specify that it should be called when the event which corresponds to the function name is emitted. Here is an example where the robot toggles its top RGB led between yellow and switched off every 0.5 second.
```
on = False
timer_period[0] = 500
@onevent
def timer0():
    global on, leds_top
    on = not on
    if on:
        leds_top = [32, 32, 0]
    else:
        leds_top = [0, 0, 0]
```

You can copy-paste the code above to the repl. We show it below with the repl prompts, which as usual you must not type:
```
>>> on = False
>>> timer_period[0] = 500
>>> @onevent
... def timer0():
...     global on, leds_top
...     on = not on
...     if on:
...         leds_top = [32, 32, 0]
...     else:
...         leds_top = [0, 0, 0]
...
>>>
```

Once you've defined the function in Python running on your computer, nothing more happens. On the Thymio, there is just the variable `timer.period[0]` which has been set to 500. The magic happens with the `run()` function:
```
>>> run()
>>>
```

The TDM repl will gather all the functions decorated with `@onevent`, all the Thymio variables which have been assigned to, global variables and other functions called from `@onevent` functions (directly or not), and make a Python program for the Thymio with all that. Then this program is converted to the Aseba programming language (the language accepted by the TDM), sent to the Thymio and executed.

If you want to check what `run()` does behind the scenes, call `robot_code()` to get the Python program, or `robot_code("aseba")` to get its conversion to Aseba:
```
>>> print(robot_code())
timer_period = [500, 0]
@onevent
def timer0():
    global on, leds_top
    on = not on
    if on:
        leds_top = [32, 32, 0]
    else:
        leds_top = [0, 0, 0]
on = False

>>> print(robot_code("aseba"))
var on
var _timer0__tmp[1]

timer.period = [500, 0]
on = 0

onevent timer0
    if on == 0 then
        _timer0__tmp[0] = 1
    else
        _timer0__tmp[0] = 0
    end
    on = _timer0__tmp[0]
    if on != 0 then
        leds.top = [32, 32, 0]
    else
        leds.top = [0, 0, 0]
    end

>>>
```

To retrieve data from the robot and process them further or store them on your computer, you can send events with `emit`. Let's write a short demonstration. But first, to avoid any interference with our previous definitions, we ask Python to forget the list of `@onevent` functions and assignments to Thymio's variables:
```
robot_code_new()
```

Here is a short program which collects 20 samples of the front proximity sensor, one every 200ms (5 per second), i.e. during 4 seconds:
```
i = 0
timer_period[0] = 200

@onevent
def timer0():
    global i, prox_horizontal
    i += 1
    if i > 20:
        exit()
    emit("front", prox_horizontal[2])
```

Note how the Thymio program terminates with a call to the `exit()` function. Running it is done as usual with `run()`. Since the program emits events, `run` continues running to process the events it receives until it receives `_exit` (emitted by `exit()`) or you type control-C. All events, except for `_exit` and `_print`, are collected with their data. Event data are retrieved with `get_event_data(event_name)`:
```
>>> run()  # 4 seconds to move your hand in front of the robot
>>> get_event_data("front")
[[0], [0], [0], [0], [1732], [2792], [4182], [4325], [3006], [1667], [0], [1346], [2352], [3972], [4533], [2644], [1409], [0], [0], [0], [0]]
```

You can send events with different names. You can also reset an event collection by calling `clear_event_data(event_name)`, or without argument to clear all the events:
```
>>> clear_event_data()
```

We've mentionned the `_print` event. It's emitted by the `print()` function, an easy way to check what the program does. The Thymio robot is limited to handling integer numbers, but `print` still accepts constant strings. The robot and the computer work together to display what's expected.
```
>>> robot_code_new()
>>> @onevent
... def button_forward():
...    print("Temperature:", temperature)
...
>>> run()  # press the forward button a few times, then control-C
Temperature: 292
Temperature: 293
^C
```
