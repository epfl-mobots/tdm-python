## Jupyter notebooks

Jupyter notebooks offer a nice alternative to the plain Python prompt in a terminal. In notebooks, you can easily store a sequence of commands, edit them, repeat them, document them, have larger code fragments, produce graphics, or have interactive controls such as sliders and checkboxes. This section describes features specific to the use of tdmclient to connect and interact with a Thymio II robot. For general informations about Jupyter, how to install it and how to open an existing notebook or create a new one, please refer to its [documentation](https://jupyter.org/).

The next subsections describe how to install tdmclient in the context of a notebook, how to connect and interact with a robot with the classes and methods of tdmclient, and how to have a notebook where variables are synchronized with the robot's (the equivalent of the TDM repl).

### Installing tdmclient in a notebook

In notebooks, the context of Python is not the same as when you run it in a terminal window. To make sure that tdmclient is available, you can have a code cell with the following content at the beginning of your notebook and evaluate it before importing tdmclient:
```
%pip install --upgrade tdmclient
```

This will make sure you have the last version available at [https://pypi.org](https://pypi.org).

Alternatively, if you develop your own version of tdmclient, you can make a `.whl` file by typing the following command in a terminal:
```
python3 setup.py bdist_wheel
```
Then in your notebook, replace the `%pip` cell above with
```
%pip install --force-reinstall /.../tdm-python/dist/tdmclient-0.1.3-py3-none-any.whl
```
replacing `/.../tdm-python/dist/tdmclient-0.1.3-py3-none-any.whl` with the actual location of the `.whl` file.

### Using tdmclient classes and methods

This section describes the use of the class `ClientAsync` in a notebook.

The main difference between using tdmclient in a notebook and in the standard Python repl (read-eval-print loop) is that you can use directly the `await` keyword to execute `async` methods and wait for their result. Therefore:
- You can avoid writing async functions if it's just to run them with `run_async_program`.
- If you still write async functions, run them with `await prog()` instead of `client.run_async_program(prog)`.

In the code fragments below, you can put separate statements in distinct cells and intersperse text cells. Only larger Python constructs such as `with`, loops, or function definitions, must be contained as a whole in a single cell.

First, import what's needed from the tdmclient package, create client and node object, and lock the node to be able to set variables or run programs:
```
from tdmclient import ClientAsync
client = ClientAsync()
node = await client.wait_for_node()
await node.lock()
```

Then continue as with the Python repl, just replacing `aw(...)` with `await ...`.

### Synchronized variables

This section parallels the TDM repl where the Thymio variables are shared with your local Python session.

First, import what's needed from the tdmclient package and start the session:
```
import tdmclient.notebook
await tdmclient.notebook.start()
```

Then the variables which match the robot's are synchronized in both directions. Dots are replaced by underscores: `leds.top` on Thymio becomes `leds_top` in Python.
```
# cyan
leds_top = [0, 32, 32]
```

You can also define event handlers with functions decorated with `@onevent`:
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

Run and stop them with `run()` and `stop()`, respectively.

`run()` collects all the event handlers, the functions they call, the Thymio variables which have been set, and other global variables they use to make a Python program to be converted from Python to Aseba, compiled, and run on the Thymio. But you can also provide program code as a whole in a cell and perform these steps separately:
```
%%run_python
v = [32, 0, 32, 0, 32, 0, 32, 0]
leds_circle = v
```
```
%%run_aseba
var v[] = [32, 32, 32, 0, 0, 0, 32, 32]
leds.circle = v
```
```
%%transpile_to_aseba
v = [32, 0, 32, 0, 32, 0, 32, 0]
leds_circle = v
```

### Custom events

To retrieve data from the robot and process them further in your notebook, you can send events with `emit`. In the program below, we collects 20 samples of the front proximity sensor, one every 200ms (5 per second), i.e. during 4 seconds.
```
%%run_python --wait

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

Events received by the computer are collected automatically. We retrieve them with `get_event_data(event_name)`, a list of all the data sent by `emit`, which are lists themselves.
```
data = get_event_data("front")
print(data)
```

You can send events with different names. You can also reset an event collection by calling `clear_event_data(event_name)`, or without argument to clear all the events:
```
clear_event_data()
```

You can also send events in the other direction, from the notebook to the robot. This can be useful for instance if you implement a low-level behavior on the robot, such as obstacle avoidance and sensor acquisition, and send at a lower rate high-level commands which require more computing power available only on the PC.

The Thymio program below listens for events named `color` and changes the top RGB led color based on a single number. Bits 0, 1 and 2 represent the red, green, and blue components respectively.
```
%%run_python

@onevent
def color(c):
    global leds_top
    leds_top[0] = 32 if c & 1 else 0
    leds_top[1] = 32 if c & 2 else 0
    leds_top[2] = 32 if c & 4 else 0
```

Now that the program runs on the robot, we can send it `color` events. The number of values in `send_event` should match the `@onevent` declaration. They can be passed as numeric arguments or as arrays.
```
for col in range(8):
    send_event("color", col)
    sleep(0.5)
```
