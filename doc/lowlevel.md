
## tdmclient classes and objects

### Interactive Python

This section will describe only the use of `ClientAsync`, the highest-level way to interact with a robot, with asynchronous methods which behave nicely in a non-blocking way if you need to perform other tasks such as running a user interface. All the tools described above use `ClientAsync`, except for `tdmclient.tools.tdmdiscovery` which doesn't communicate with the robots.

First we'll type commands interactively by starting Python&nbsp;3 without argument. To start Python&nbsp;3, open a terminal window (Windows Terminal or Command Prompt in Windows, Terminal in macOS or Linux) and type `python3`. TDM replies should arrive quicker than typing at the keyboard. Next section shows how to interact with the TDM from a program where you wait for replies and use them immediately to run as fast as possible.

Start Python&nbsp;3, then import the required class. We also import the helper function `aw`, an alias of the static method `ClientAsync.aw` which is useful when typing commands interactively.
```
from tdmclient import ClientAsync, aw
```

Create a client object:
```
client = ClientAsync()
```

If the TDM runs on your local computer, its address and port number will be obtained from zeroconf. You can check their value:
```
client.tdm_addr
```
```
client.tdm_port
```

The client will connect to the TDM which will send messages to us, such as one to announce the existence of a robot. There are two ways to receive and process them:
- Call explicitly
    ```
    client.process_waiting_messages()
    ```
    If a robot is connected, you should find its description in an array of nodes in the client object:
    ```
    node = client.nodes[0]
    ```
- Call an asynchronous function in such a way that its result is waited for. This can be done in a coroutine, a special function which is executed at the same time as other tasks your program must perform, with the `await` Python keyword; or handled by the helper function `aw`. In plain Python, keyword `await` is valid only in a function, hence we cannot call it directly from the Python prompt (IPython, an improved command interpreter which is used in Jupyter, supports directly `await`). In this section, we'll use `aw`. Robots are associated to nodes. To get the first node once it's available (i.e. an object which refers to the first or only robot after having received and processed enough messages from the TDM to have this information), type
    ```
    node = aw(client.wait_for_node())
    ```
    Avoiding calling yourself `process_waiting_messages()` is safer, because other methods like `wait_for_node()` make sure to wait until the expected reply has been received from the TDM.

The value of `node` is an object which contains some properties related to the robot and let you communicate with it. The node id is displayed when you just print the node:
```
node
```
or
```
print(node)
```

It's also available as a string:
```
node_id_str = node.id_str
```

The node properties are stored as a dict in `node.props`. For example `node.props["name"]` is the robot's name, which you can change:
```
aw(node.rename("my white Thymio"))
```

Lock the robot to change variables or run programs (make sure it isn't already used in Thymio Suite):
```
aw(node.lock())
```

Compile and load an Aseba program:
```
program = """
var on = 0  # 0=off, 1=on
timer.period[0] = 500

onevent timer0
    on = 1 - on  # "on = not on" with a syntax Aseba accepts
    leds.top = [32 * on, 32 * on, 0]
"""
r = aw(node.compile(program))
```

The result `r` is None if the call is successful, or an error number if it has failed. In interactive mode, we won't store anymore the result code if we don't expect and check errors anyway. But it's usually a good thing to be more careful in programs.

No need to store the actual source code for other clients, or anything at all.
```
aw(node.set_scratchpad("Hello, Studio!"))
```

Run the program compiled by `compile`:
```
aw(node.run())
```

Stop it:
```
aw(node.stop())
```

Make the robot move forward by setting both variables `motor.left.target` and `motor.right.target`:
```
v = {
    "motor.left.target": [50],
    "motor.right.target": [50],
}
aw(node.set_variables(v))
```

Make the robot stop:
```
v = {
    "motor.left.target": [0],
    "motor.right.target": [0],
}
aw(node.set_variables(v))
```

Unlock the robot:
```
aw(node.unlock())
```

Getting variable values is done by observing changes, which requires a function; likewise to receive events. This is easier to do in a Python program file. We'll do it in the next section.

Here is how to send custom events from Python to the robot. The robot must run a program which defines an `onevent` event handler; but in order to accept a custom event name, we have to declare it first to the TDM, outside the program. We'll define an event to send two values for the speed of the wheels, `"speed"`. Method `node.register_events` has one argument, an array of tuples where each tuple contains the event name and the size of its data between 0 for none and a maximum of 32. The robot must be locked if it isn't already to accept `register_events`, `compile`, `run`, and `send_events`.
```
aw(node.lock())
aw(node.register_events([("speed", 2)]))
```

Then we can send and run the program. The event data are obtained from variable `event.args`; in our case only the first two elements are used.
```
program = """
onevent speed
    motor.left.target = event.args[0]
    motor.right.target = event.args[1]
"""
aw(node.compile(program))
aw(node.run())
```

Finally, the Python program can send events. Method `node.send_events` has one argument, a dict where keys correspond to event names and values to event data.
```
# turn right
aw(node.send_events({"speed": [40, 20]}))
# wait 1 second, or wait yourself before typing the next command
aw(client.sleep(1))
# stop the robot
aw(node.send_events({"speed": [0, 0]}))
```

### Python program

In a program, instead of executing asynchronous methods synchronously with `aw` or `ClientAsync.aw`, we put them in an `async` function and we `await` for their result. The whole async function is executed with method `run_async_program`.

Moving forward, waiting for 2 seconds and stopping could be done with the following code. You can store it in a .py file or paste it directly into an interactive Python&nbsp;3 session, as you prefer; but make sure you don't keep the robot locked, you wouldn't be able to lock it a second time. Quitting and restarting Python is a sure way to start from a clean state.
```
from tdmclient import ClientAsync

def motors(left, right):
    return {
        "motor.left.target": [left],
        "motor.right.target": [right],
    }

client = ClientAsync()

async def prog():
    node = await client.wait_for_node()
    await node.lock()
    await node.set_variables(motors(50, 50))
    await client.sleep(2)
    await node.set_variables(motors(0, 0))
    await node.unlock()

client.run_async_program(prog)
```

This can be simplified a little bit with the help of `with` constructs:
```
from tdmclient import ClientAsync

def motors(left, right):
    return {
        "motor.left.target": [left],
        "motor.right.target": [right],
    }

with ClientAsync() as client:
    async def prog():
        with await client.lock() as node:
            await node.set_variables(motors(50, 50))
            await client.sleep(2)
            await node.set_variables(motors(0, 0))
    client.run_async_program(prog)
```

To read variables, the updates must be observed with a function. The following program calculates a motor speed based on the front proximity sensor to move backward when it detects an obstacle. Instead of calling the async method `set_variables` which expects a result code in a message from the TDM, it just sends a message to change variables with `send_set_variables` without expecting any reply. The TDM will send a reply anyway, but the client will ignore it without trying to associate it with the request message. `sleep()` without argument (or with a negative duration) waits forever, until you interrupt it by typing control-C.
```
from tdmclient import ClientAsync

def motors(left, right):
    return {
        "motor.left.target": [left],
        "motor.right.target": [right],
    }

def on_variables_changed(node, variables):
    try:
        prox = variables["prox.horizontal"]
        prox_front = prox[2]
        speed = -prox_front // 10
        node.send_set_variables(motors(speed, speed))
    except KeyError:
        pass  # prox.horizontal not found

with ClientAsync() as client:
    async def prog():
        with await client.lock() as node:
            await node.watch(variables=True)
            node.add_variables_changed_listener(on_variables_changed)
            await client.sleep()
    client.run_async_program(prog)
```

Compare with an equivalent Python program running directly on the Thymio:
```
@onevent
def prox():
    global prox_horizontal, motor_left_target, motor_right_target
    prox_front = prox_horizontal[2]
    speed = -prox_front // 10
    motor_left_target = speed
    motor_right_target = speed
```

You could save it as a .py file and run it with `tdmclient.tools.run` as explained above. If you want to do everything yourself, to understand precisely how tdmclient works or because you want to eventually combine processing on the Thymio and on your computer, here is a Python program running on the PC to convert it to Aseba, compile and load it, and run it.
```
from tdmclient import ClientAsync
from tdmclient.atranspiler import ATranspiler

thymio_program_python = r"""
@onevent
def prox():
    global prox_horizontal, motor_left_target, motor_right_target
    prox_front = prox_horizontal[2]
    speed = -prox_front // 10
    motor_left_target = speed
    motor_right_target = speed
"""

# convert program from Python to Aseba
thymio_program_aseba = ATranspiler.simple_transpile(thymio_program_python)

with ClientAsync() as client:
    async def prog():
        with await client.lock() as node:
            error = await node.compile(thymio_program_aseba)
            error = await node.run()
    client.run_async_program(prog)
```

### Cached variables

tdmclient offers a simpler way, if slightly slower, to obtain and change Thymio variables. They're accessible as `node["variable_name"]` or `node.v.variable_name`, both for getting and setting values, also when `variable_name` contains dots. Here is an alternative implementation of the remote control version of the program which makes the robot move backward when an obstacle is detected by the front proximity sensor.
```
from tdmclient import ClientAsync

with ClientAsync() as client:
    async def prog():
        with await client.lock() as node:
            await node.wait_for_variables({"prox.horizontal"})
            while True:
                prox_front = node.v.prox.horizontal[2]
                speed = -prox_front // 10
                node.v.motor.left.target = speed
                node.v.motor.right.target = speed
                node.flush()
                await client.sleep(0.1)
    client.run_async_program(prog)
```

Scalar variables have an `int` value. Array variables are iterable, i.e. they can be used in `for` loops, converted to lists with function `list`, and used by functions such as `max` and `sum`. They can be stored as a whole and retain their link with the robot: getting an element retieves the most current value, and setting an element caches the value so that it will be sent to the robot by the next call to `node.flush()`.
Here is an interactive session which illustrates what can be done.
```
>>> from tdmclient import ClientAsync
>>> client = ClientAsync()
>>> node = client.aw(client.wait_for_node())
>>> client.aw(node.wait_for_variables({"leds.top"}))
>>> rgb = node.v.leds.top
>>> rgb
Node array variable leds.top[3]
>>> list(rgb)
[0, 0, 0]
>>> client.aw(node.lock_node())
>>> rgb[0] = 32  # red
>>> node.var_to_send
{'leds.top': [32, 0, 0]}
>>> node.flush()  # robot turns red
```
