# Examples of programs running on the robot

This directory contains programs written in Aseba or Python. Tool `tdmclient.tools.run` recognize the programming language thanks to the file extension.

To run program `green.py`, for example, type the following command in a terminal:

```
python3 -m tdmclient.tools.run examples/robot/green.py
```

To stop the program:

```
python3 -m tdmclient.tools.run --stop
```

## blue.aseba

One-line program to switch the top led to blue.

## green.py

One-line program to switch the top led to green

## blink.aseba blink.py

Toggle the top led between yellow and switched off. The two programs show the differences between Aseba and Python.

## backward.py

Make the robot move backward when something close is detected by the front proximity sensor.

## exit.py

Demonstration of the `exit()` function. The purpose of `exit()` is to ask the computer to consider that the robot program is finished, not to stop the robot program by itself.

The program switches on progressively each of the 8 yellow leds which make a circle, then calls `exit()`. At that time, an event is sent to the computer and `tdmclient.tools.run` terminates.

## print.py

Demonstration of the `print()` function. The arguments of `print()` can be constant strings and numeric expressions. When `print()` is executed, it sends an event to the computer with an identifier and the numeric values. Tool `tdmclient.tools.run` uses the identifier to retrieve the strings and display the expected information.

## acquisition.py

Demonstration of custom events. The value of the front proximity sensor is sent to the computer which displays it.

## clock.py

Demonstration of module `clock`. Touching the Thymio buttons has the following effect:

- left: print the value of `clock.seconds()`, the number of seconds elapsed since the start of the program or the last time `clock.reset()` was called
- right: print the value of `clock.ticks_50Hz()`, the number of 1/50 seconds elapsed since the start of the program or the last time `clock.reset()` was called
- backward: call `clock.reset()`
- center: call `exit()`, which terminates `tdmclient.tools.run`
