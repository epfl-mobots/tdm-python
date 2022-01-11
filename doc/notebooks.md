
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
%pip install --quiet --force-reinstall /.../tdm-python/dist/tdmclient-0.1.3-py3-none-any.whl
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

Variables accessed or changed in the notebook are synchronized with the robot only if the statements are located directly in notebook cells. This isn't automatically the case for functions, to let you decide when it's efficient to receive or send values to the robot. There are two ways to do it:
- Function `get_var("var1", "var2", ...)` retrieves the value of variables `var1`, `var2` etc. and returns them in a tuple in the same order. The typical use is to unpack the tuple directly into variables in an assignment: `var1,var2,...=get_var("var1","var2",...)`; beware to have a trailing comma if you retrieve only one variable, else you'll get a plain assignment of the tuple itself.

    Function `set_var(var1=value1,var2=value2,...)` sends new values to the robot.

    Here is an example which sets the color of the robot to red or blue depending on its temperature:
    ```
    def f(temp_limit=30):
        temperature, = get_var("temperature")
        if temperature > temp_limit * 10:
            set_variables({"leds_top": [32, 0, 0]})
        else:
            set_variables({"leds_top": [0, 10, 32]})
    ```
- To synchronized global variables whose names match the robot's, the function can be decorated with `@tdmclient.notebook.sync_var`. The effect of the decorator is to extend the function so that these variables are fetched at the beginning and sent back to the robot before the function returns.

    Here is the same example:
    ```
    @tdmclient.notebook.sync_var
    def f(temp_limit=30):
        global temperature, leds_top
        if temperature > temp_limit * 10:
            leds_top = [32, 0, 0]
        else:
            leds_top = [0, 10, 32]
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

Instead of calling `clear_event_data()` without argument, the option `--clear-event-data` of the magic command `%%run_python` has the same effect and avoids to evaluate a separate notebook cell.

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

### Connection and disconnection

Usually, once we've imported the notebook support with `import tdmclient.notebook`, we would connect to the first robot, assuming there is just one. It's also possible to get the list of robots:
```
await tdmclient.notebook.list()
```
```
id:       67a5510c-d1af-4386-9458-d9145d951664
group id: 7dcf1f69-85a8-4fd4-9c4b-b74d155a1246
name:     AA003
status:   2 (available)
cap:      7
firmware: 14
```

When you start the notebook session, you can add options to `tdmclient.notebook.start` to specify which robot to use. Robots can be identified by their id, which is unique hence unambiguous but difficult to type and remember, or by their name which you can define yourself.

Since we don't know the id or name of your robot, we'll cheat by picking the actual id and name of the first robot. To get the list of robots (or nodes), instead of `tdmclient.notebook.list` as above where the result is displayed in a nice list of properties, we call `tdmclient.notebook.get_nodes` which returns a list.
```
nodes = await tdmclient.notebook.get_nodes()
id_first_node = nodes[0].id_str
name_first_node = nodes[0].props["name"]
print(f"id: {id_first_node}")
print(f"name: {name_first_node}")
```
```
id: 67a5510c-d1af-4386-9458-d9145d951664
name: AA003
```

Then you can specify the robot id:
```
await tdmclient.notebook.start(node_id=id_first_node)
```

We want to show you how to use the robot's name instead of its id, but first we must close the connection:
```
await tdmclient.notebook.stop()
```

Now the robot is available again.
```
await tdmclient.notebook.start(node_name=name_first_node)
```

### Addressing robots

When several robots are connected to the computer, access to the default (first or specified in `start()`) robot's variables, running or stopping a program is done as if there was no other robot connected to the TDM. To refer to another robot, you have to specify it, with options in magic commands `%%run_python` or `%%run_aseba`, and with key arguments in functions `run()` or `stop()`. In all cases, you can do it with the node id, the node name, or the node index, a number which is 0 for the first robot (the default robot used by `tdmclient.notebook.start()`), 1 for the second robot and so on.

| Robot specification | Magic command option | Function key argument |
| --- | --- | --- |
| id | `--robotid ...` | `robot_id="..."` |
| name | `--robotname ...` | `robot_name="..."` |
| index | `--robotindex ...` | `robot_index="..."` |

If the robot name contains spaces, enclose it between double-quotes also for the magic command option:
```
%%run_python --robotname "my Thymio"
...
```

To have a notebook which works unmodified with any robots, not only those of its author, we'll use the robot index. We'll also include it for the default robot (`robot_index=0`) to make clear it's one among a group of two robots.

To illustrate running programs on specific robots, here is how to change the color of the top led to blue on robot 0 and green on robot 1:
```
%%run_python --robotindex 0
leds_top = [0, 0, 32]
```
```
%%run_python --robotindex 1
leds_top = [0, 20, 0]
```

If you want to run the same program on multiple robots, you can do it with a single `%%run_python` or `%%run_aseba` cell by specifying the id, name or index of all the target robots separated with commas, without additional spaces. If the robot names contain spaces, enclose the whole list of names between double-quotes, keeping exactly the spaces in the names but without additional spaces around the commas.
```
%%run_aseba --robotindex 0,1
leds.bottom.right = [32, 0, 32]  # purple
leds.bottom.left = [32, 16, 0]   # orange
```

When the option `--wait` is specified, the cell execution proceeds until each program has called `exit()` (in Python), or the execution is interrupted. The output of `print()` functions, and `exit(status)` functions with a non-zero status, is prefixed with the index of the robot among those the program run on. (In the following program, since `exit()` just sends an `_exit` event to the computer without terminating immediately itself its own execution on the robot, `print()` is executed one more time).
```
%%run_python --robotindex 0,1 --wait

timer_period[0] = 250
i = 0

@onevent
def timer0():
    global i
    i += 1
    if i > 3:
        exit(1)
    print(i)
```
```
[R0] 1
[R0] 2
[R0] 3
[R1] 1
[R0] Exit, status=1
[R1] 3
[R1] Exit, status=1
[R1] 4
```

### Controlling multiple robots with events from Jupyter

Function `get_event_data()` retrieves the events sent by a robot. It can take a key argument `robot_id`, `robot_name` or `robot_index` to specify which robot is concerned.

To illustrate this, here is a program which emits an event `"b"` with data suitable for `leds_circle`. It accepts an event `"c"` to set `leds_circle`. We run it on both robots (`--robotindex 0,1`).
```
%%run_python --robotindex 0,1 --clear-event-data

@onevent
def button_center():
    emit("b", 0, 0, 0, 0, 0, 0, 0, 0)
@onevent
def button_forward():
    emit("b", 32, 32, 0, 0, 0, 0, 0, 32)
@onevent
def button_right():
    emit("b", 0, 32, 32, 32, 0, 0, 0, 0)
@onevent
def button_backward():
    emit("b", 0, 0, 0, 32, 32, 32, 0, 0)
@onevent
def button_left():
    emit("b", 0, 0, 0, 0, 0, 32, 32, 32)

@onevent
def c(l0, l1, l2, l3, l4, l5, l6, l7):
    global leds_circle
    leds_circle = [l0, l1, l2, l3, l4, l5, l6, l7]
```

We make the robot communicate by forwarding the messages in Jupyter. When Jupyter receives events, the robot sender is identified by a node object. In order to deduce which is the receiver robot, we first get the list of all nodes.
```
nodes = await tdmclient.notebook.get_nodes()
```

If the sender is `node` then its index is `nodes.index(node)` and the index of the receiver (the other among the first two robots) is `1-nodes.index(node)`.

Here is a program to forward the events. Touch the buttons on one robot to switch corresponding leds on the other one. The loop runs until you interrupt it with the Interrupt button (little black square).
```
def on_event_data(node, event_name):
    src_index = nodes.index(node)
    dest_index = 1 - src_index
    event_data_list = get_event_data("b", robot_index=src_index)
    for data in event_data_list:
        send_event("c", *data, robot_index=dest_index)
    clear_event_data("b", robot_index=src_index)

tdmclient.notebook.process_events(all_nodes=True, on_event_data=on_event_data)
```

### Infrared communication between robots

Simple messages made of a single number can be sent between robots via the same infrared leds and sensors as those used as active proximity sensors. The program below reproduces the same behavior as the robot and computer programs in the previous section, where touching a button switches on the corresponding yellow leds of the other robot. Once the robot programs are launched, the computer isn't involved anymore.
```
%%run_python --robotindex 0,1

nf_prox_comm_enable(True)

def send_msg(code):
    global prox_comm_tx
    prox_comm_tx = code

@onevent
def button_center():
    send_msg(99)
@onevent
def button_forward():
    send_msg(1)
@onevent
def button_right():
    send_msg(2)
@onevent
def button_backward():
    send_msg(3)
@onevent
def button_left():
    send_msg(4)

@onevent
def prox_comm():
    global prox_comm_rx, leds_circle
    msg = prox_comm_rx
    if msg == 99:
        leds_circle = [0, 0, 0, 0, 0, 0, 0, 0]
    elif msg == 1:
        leds_circle = [32, 32, 0, 0, 0, 0, 0, 32]
    elif msg == 2:
        leds_circle = [0, 32, 32, 32, 0, 0, 0, 0]
    elif msg == 3:
        leds_circle = [0, 0, 0, 32, 32, 32, 0, 0]
    elif msg == 4:
        leds_circle = [0, 0, 0, 0, 0, 32, 32, 32]
```

### Direct use of node objects

Once connected, the node object used to communicate with the robot can be obtained with `get_node()`:
```
robot = tdmclient.notebook.get_node()
```

Then all the methods and properties defined for `ClientAsyncCacheNode` objects can be used. For example, you can get the list of its variables:
```
robot_variables = list(await robot.var_description())
robot_variables
```
```
['_id',
 'event.source',
 'event.args',
 ...
 'sd.present']
 ```

Or set the content of the scratchpad, used by the tdm to share the source code amoung all the clients. No need to use the actual source code, you can set it to any string. Check then in Aseba Studio.
```
await robot.set_scratchpad("Hello from a notebook, Studio!")
```

The client object is also available as a `ClientAsync` object:
```
client = tdmclient.notebook.get_client()
```

The client object doesn't have many intersting usages, because there are simpler alternatives with higher-level functions. Let's check whether the tdm is local:
```
client.localhost_peer
```
```
True
```

### Interactive widgets

This section illustrates the use of `tdmclient.notebook` with interactive widgets provided by the `ipywidgets` package.

Import the required classes and connect to the robot. In addition to `tdmclient.notebook`, `ipywidgets` provides support for interactive widgets, i.e. GUI elements which you can control with the mouse.
```
import tdmclient.notebook
from ipywidgets import interact, interactive, fixed, interact_manual
import ipywidgets as widgets
await tdmclient.notebook.start()
```

A function can be made interactive by adding a decorator `@interact` which specifies the range of values of each argument. When the cell is executed, sliders are displayed for each interactive argument. `(0,32,1)` means a range of integer values from 0 to 32 with a step of 1. Since the default value of the step is 1, we can just write `(0,32)`. The initial value of the arguments is given by their default value in the function definition.

Thymio variables aren't synchronized automatically when they're located inside functions. By adding a decorator `@tdmclient.notebook.sync_var`, all Thymio variables referenced in the function are fetched from the robot before the function execution and sent back to the robot afterwards. Note the order of the decorators: `@tdmclient.notebook.sync_var` modifies the function to make its variables synchronized with the robot, and `@interact` makes this modified function interactive.
```
@interact(red=(0,32), green=(0,32), blue=(0,32))
@tdmclient.notebook.sync_var
def rgb(red=0, green=0, blue=0):
    global leds_top
    leds_top = [red, green, blue]
```

Here are alternative ways for the same result. Instead of a decorator in front of the function, you can call `interact` as a normal function, passing it the function whose arguments are manipulated interactively. Instead of decorating the function with `@tdmclient.notebook.sync_var`, you can call explicitly `set_var` to change the robot variables. And if your function is just a simple expression (a call to `set_var` or to another function if the values of its arguments don't fit directly the sliders of `interact`), you can replace it with a lambda expression.
```
interact(lambda red=0,green=0,blue=0: set_var(leds_top=[red,green,blue]), red=(0,32), green=(0,32), blue=(0,32));
```

You can combine a program running on the robot and interactive controls in the notebook to change variables. Here is a program which uses its front proximity sensor to remain at some distance from an obstacle. Put your hand or a white box in front of the Thymio before you run the cell, or be ready to catch it before it falls off the table.
```
%%run_python

prox0 = 1000
gain_prc = 2
timer_period[0] = 100

@onevent
def timer0():
    global prox_horizontal, motor_left_target, motor_right_target, prox0, gain_prc
    speed = math_muldiv(prox0 - prox_horizontal[2], gain_prc, 100)
    motor_left_target = speed
    motor_right_target = speed
```

The global variables created by the program are also synchronized with those in the notebook:
```
prox0
```
```
1000
```
```
gain_prc = 5
```

Changing the value of `prox0`, which is related to the distance the robot will maintain with respect to the obstacle, can be done with a slider as for `leds_top` above:
```
@interact(prox_target=(0, 4000, 10))
@tdmclient.notebook.sync_var
def change_prox0(prox_target):
    global prox0
    prox0 = prox_target
```

Change the value of the target value of the proximity sensor with the slider and observe how the robot moves backward or forward until it reaches a position where the expression `prox0 - prox_horizontal[2]` is 0, hence the speed is 0. Actually because it's unlikely the sensor reading remains perfectly constant, the robot will continue making small adjustments.

When you've finished experimenting, stop the program:
```
stop()
```

### Graphics

The usual Python module for graphics is `matplotlib`. To plot a sensor value, or any computed value, as a function of time, you can retrieve the values with events.
```
import matplotlib.pyplot as plt
```

We can begin with the example presented to illustrate the use of events:
```
%%run_python --clear-event-data --wait

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

Then we retrieve and plot the event data:
```
%matplotlib inline
prox_front = get_event_data("front")
plt.plot(prox_front);
```

The horizontal scale shows the sample index, from 0 to 20 (the `_exit` event sent by the call to `exit()` is processed by the PC after the complete execution of `timer0()`; thus the program emits values for `i` from 1 to 21).

You may prefer to use a time scale. If the events are produced in a timer event at a known rate, the time can be computed in the notebook. But often it's more convenient to get the actual time on the robot by reading its clock. For that, we use the `ticks_50Hz()` function defined in the `clock` module, which returns a value incremented 50 times per second. Instead of counting samples, we stop when the clock reaches 4 seconds. Both `clock.ticks_50Hz()` and `clock.seconds()` are reset to 0 when the program starts or when `clock.reset()` is called. Here is a new version of the robot program:
```
%%run_python --clear-event-data --wait

import clock

timer_period[0] = 200

@onevent
def timer0():
    global prox_horizontal
    if clock.seconds() >= 4:
        exit()
    emit("front", clock.ticks_50Hz(), prox_horizontal[2])
```

The events produced by `emit()` contain 2 values, the number of ticks and the front proximity sensor. We can extract them into `t` and `y` with list comprehensions, a compact way to manipulate list values. The time is converted to seconds as fractional number, something which cannot be done on the Thymio where all numbers are integers.
```
%matplotlib inline
prox_front = get_event_data("front")
t = [data[0] / 50 for data in prox_front]
y = [data[1] for data in prox_front]
plt.plot(t, y);
```

### Live graphics

Support for animated graphics, where new data are displayed when there're available, depends on the version of Jupyter and the extensions which are installed. This section describes one way to update a figure in JupyterLab without any extension.

We modify the program and plot above to run continuously with a sliding time window of 10 seconds. The call to `exit()` is removed from the robot program, and we don't wait for the program to terminate.
```
%%run_python --clear-event-data

import clock

timer_period[0] = 200

@onevent
def timer0():
    global prox_horizontal
    emit("front", clock.ticks_50Hz(), prox_horizontal[2])
```

The figure below displays the last 10 seconds of data in a figure which is updated everytime new events are received. For each event received, the first data value is the time in 1/50 second, and the remaining values are displayed as separate lines. Thus you can keep the same code with different robot programs, as long as you emit events with a unique name and a fixed number of values.

Click the stop button in the toolbar above to interrupt the kernel (the Python session which executes the notebook cells).
```
from IPython.display import clear_output
from matplotlib import pyplot as plt
%matplotlib inline

def on_event_data(node, event_name):

    def update_plot(t, y, time_span=10):
        clear_output(wait=True)
        plt.figure()

        if len(t) > 1:
            plt.plot(t, y)
            t_last = t[-1]
            plt.xlim(t_last - time_span, t_last)

        plt.grid(True)
        plt.show();

    data_list = get_event_data(event_name)
    t = [data[0] / 50 for data in data_list]
    y = [data[1:] for data in data_list]

    update_plot(t, y)

clear_event_data()
tdmclient.notebook.process_events(on_event_data)
```
