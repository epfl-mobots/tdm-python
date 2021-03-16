# tdmclient

Python package to connect to a [Thymio II robot](https://thymio.org) via the Thymio Device Manager (TDM), a component of the Thymio Suite. The connection between Python and the TDM is done over TCP to the port number advertised by zeroconf.

## Examples

Connect a robot to your computer via a USB cable or the RF dongle and launch Thymio Suite. In Thymio Suite, you can click the Aseba Studio icon to check that the Thymio is recognized, and, also optionally, start Aseba Studio (select the robot and click the button "Program with Aseba Studio"). Only one client can control the robot at the same time to change a variable or run a program. If that's what you want to do from Python, either don't start Aseba Studio or unlock the robot by clicking the little lock icon in the tab title near the top left corner of the Aseba Studio window.

Some features of the library can be accessed directly from the command window by typing `python3 -m tdmclient.tools.abc arguments`, where `abc` is the name of the tool.

### tdmclient.tools.tdmdiscovery

Display the address and port of TDM advertised by zeroconf until control-C is typed:
```
python3 -m tdmclient.tools.tdmdiscovery
```

### tdmclient.tools.run

Run an Aseba program on the first Thymio II robot and store it into the scratchpad so that it's seen in Aseba Studio:
```
python3 -m tdmclient.tools.run --scratchpad examples.blink.aseba
```

Stop the program:
```
python3 -m tdmclient.tools.run --stop
```

Display other options:
```
python3 -m tdmclient.tools.run --help
```


### tdmclient.tools.watch

Display all node changes (variables, events and program in the scratchpad) until control-C is typed:
```
python3 -m tdmclient.tools.watch
```

### tdmclient.tools.variables

Run the variable browser in a window. The GUI is implemented with TK.
```
python3 -m tdmclient.tools.variables
```

At launch, the robot is unlocked, i.e. the variables are just fetched and displayed: _Observe_ is displayed in the status area at the bottom of the window. To be able to change them, activate menu Robot>Control. Then you can click any variable, change its value and type Return to confirm or Esc to cancel.

### Interactive Python

This section will describe only the use of `ClientAsync`, the highest-level way to interact with a robot, with asynchronous methods which behave nicely in a non-blocking way if you need to perform other tasks such as running a user interface. All the tools described above use `ClientAsync`, except for `tdmclient.tools.tdmdiscovery` which doesn't communicate with the robots.

First we'll type commands interactively by starting Python&nbsp;3 without argument. To start Python&nbsp;3, open a terminal window (Windows Terminal or Command Prompt in Windows, Terminal in macOS or Linux) and type `python3`. TDM replies should arrive quicker than typing at the keyboard. Next section shows how to interact with the TDM from a program where you wait for replies and use them immediately to run as fast as possible.

Start Python&nbsp;3, then import the required class:
```
from tdmclient import ClientAsync
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

The client will connect to the TDM which will send messages to us, such as one to announce the existence of a robot. There are two ways to accept and process them:
- Call explicitly
    ```
    client.process_waiting_messages()
    ```
    If a robot is connected, you should find its description in an array of nodes in the client object:
    ```
    node = client.nodes[0]
    ```
- Call an asynchronous function in such a way that its result is waited for. This can be done in a coroutine, a special function which is executed at the same time as other tasks your program must perform, with the `await` Python keyword; or handled by the helper function `ClientAsync.aw`. Keyword `await` is valid only in a function, hence we cannot call it directly from the Python prompt. In this section, we'll use `ClientAsync.aw`. Robots are associated to nodes. To get the first node once it's available (i.e. an object which refers to the first or only robot after having received and processed enough messages from the TDM to have this information), type
    ```
    node = ClientAsync.aw(client.wait_for_node())
    ```
    Avoiding calling yourself `process_waiting_messages()` is safer, because other methods like `wait_for_node()` make sure to wait until the expected reply has been received from the TDM.

The value of `node` is a dict which contains some properties related to the robot. Most functions use just the node id as a string:
```
node_id_str = node["node_id_str"]
```

Lock the robot to change variables or run programs (make sure it isn't already used in Thymio Suite):
```
r = ClientAsync.aw(client.lock_node(node_id_str))
```
The result `r` is None if the call is successful, or an error number if it has failed.

Compile and load an Aseba program:
```
program = """
var on = 0  # 0=off, 1=on
timer.period[0] = 500

onevent timer0
    on = 1 - on  # "on = not on" with a syntax Aseba accepts
    leds.top = [32 * on, 32 * on, 0]
"""
r = ClientAsync.aw(client.compile(node_id_str, program))
```

In interactive mode, we won't store anymore the result code if we don't expect and check errors anyway. But it's usually a good thing to be more careful in programs.

No need to store the actual source code for other clients, or anything at all.
```
ClientAsync.aw(client.set_scratchpad(node_id_str, "Hello, Studio!"))
```

Run the program compiled by `compile`:
```
ClientAsync.aw(client.run(node_id_str))
```

Stop it:
```
ClientAsync.aw(client.stop(node_id_str))
```

Make the robot move forward by setting both variables `motor.left.target` and `motor.right.target`:
```
v = {
    "motor.left.target": [50],
    "motor.right.target": [50],
}
ClientAsync.aw(client.set_variables(node_id_str, v))
```

Make the robot stop:
```
v = {
    "motor.left.target": [0],
    "motor.right.target": [0],
}
ClientAsync.aw(client.set_variables(node_id_str, v))
```

Unlock the robot:
```
ClientAsync.aw(client.unlock_node(node_id_str))
```

Getting variable values is done by observing changes, which requires a function. This is easier to do in a Python program file. We'll do it in the next section.

### Python program

In a program, instead of executing asynchronous methods synchronously with `ClientAsync.aw`, we put them in an `async` function and we `await` for their result. The whole async function is executed with method `run_async_program`.

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
    node_id_str = node["node_id_str"]
    await client.lock_node(node_id_str)
    await client.set_variables(node_id_str, motors(50, 50))
    await client.sleep(2)
    await client.set_variables(node_id_str, motors(0, 0))
    await client.unlock_node(node_id_str)

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
        with await client.lock() as node_id_str:
            await client.set_variables(node_id_str, motors(50, 50))
            await client.sleep(2)
            await client.set_variables(node_id_str, motors(0, 0))
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

def on_variables_changed(node_id_str, data):
    try:
        prox = data["variables"]["prox.horizontal"]
        prox_front = prox[2]
        speed = -prox_front // 10
        client.send_set_variables(node_id_str, motors(speed, speed))
    except KeyError:
        pass  # prox.horizontal not found

with ClientAsync() as client:
    async def prog():
        with await client.lock() as node_id_str:
            await client.watch(node_id_str, variables=True)
            client.on_variables_changed = on_variables_changed
            await client.sleep()
    client.run_async_program(prog)
```