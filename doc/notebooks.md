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
