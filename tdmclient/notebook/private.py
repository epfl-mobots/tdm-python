"""Equivalent of repl for Jupyter notebooks.
"""

_interactive_console = None
from tdmclient import ClientAsync, TDMConsole
import builtins

# define functions in tdmclient.notebook

def _pre_run_cell(info):
    _interactive_console.pre_run(info.raw_cell)

def _post_run_cell(_):
    _interactive_console.post_run()

async def get_nodes(robot_id=None, robot_name=None, timeout=5):
    """Get a list of all the robots.

    Arguments:
        robot_id - robot id to restrict the output (default: any)
        robot_name - robot name to restrict the output (default: any)
        timeout - time to obtain at least one node (default: 5s)
    """

    # try to get at least one node
    client = _interactive_console.client
    for _ in range(1 if timeout < 0.1 else int(timeout / 0.1)):
        client.process_waiting_messages()
        nodes = builtins.list(client.filter_nodes(client.nodes,
                                                  node_id=robot_id,
                                                  node_name=robot_name))
        if len(nodes) > 0:
            return nodes
        await sleep(0.1)

    return []

async def list(zeroconf=None, tdm_addr=None, tdm_port=None, password=None,
               robot_id=None, robot_name=None,
               timeout=5):
    """Display a list of all the robots.

    Arguments:
        tdm_addr - TDM address as a string (default: as in start())
        tdm_port - TDM TCP port number (default: as in start())
        password - TDM password (default: None, not necessary for local TDM)
        robot_id - robot id to restrict the output (default: any)
        robot_name - robot name to restrict the output (default: any)
        timeout - time to obtain at least one node (default: 5s)
        zeroconf - True to find TDM with zeroconf (default: automatic)
    """

    with (ClientAsync(zeroconf=zeroconf,
                      tdm_addr=tdm_addr, tdm_port=tdm_port, password=password)
          if zeroconf is not None or
             tdm_addr is not None or
             tdm_port is not None or
             _interactive_console is None
          else _interactive_console.client) as client:

        for _ in range(1 if timeout < 0.1 else int(timeout / 0.1)):
            client.process_waiting_messages()
            if len(client.nodes) > 0:
                break
            await client.sleep(0.1)

        for node in client.filter_nodes(client.nodes,
                                        node_id=robot_id, node_name=robot_name):
            print(f"id:       {node.id_str}")
            if "group_id_str" in node.props and node.props["group_id_str"] is not None:
                print(f"group id: {node.props['group_id_str']}")
            if "name" in node.props:
                print(f"name:     {node.props['name']}")
            if "status" in node.props:
                status_str = {
                    ClientAsync.NODE_STATUS_UNKNOWN: "unknown",
                    ClientAsync.NODE_STATUS_CONNECTED: "connected",
                    ClientAsync.NODE_STATUS_AVAILABLE: "available",
                    ClientAsync.NODE_STATUS_BUSY: "busy",
                    ClientAsync.NODE_STATUS_READY: "ready",
                    ClientAsync.NODE_STATUS_DISCONNECTED: "disconnected",
                }[node.status]
                print(f"status:   {node.status} ({status_str})")
            if "capabilities" in node.props:
                print(f"cap:      {node.props['capabilities']}")
            if "fw_version" in node.props:
                print(f"firmware: {node.props['fw_version']}")
            print()

async def start(zeroconf=None, tdm_addr=None, tdm_port=None, password=None,
                debug=0, **kwargs):
    """Start the connection with the Thymio and variable synchronization.

    Arguments:
        tdm_addr - TDM address as a string (default: localhost)
        tdm_port - TDM TCP port number
                   (default: standard or provided by zeroconf)
        password - TDM password (default: None, not necessary for local TDM)
        robot_id - robot node id (default: any)
        robot_name - robot name (default: any)
        zeroconf - True to find TDM with zeroconf (default: automatic)
    """

    client = ClientAsync(zeroconf=zeroconf,
                         tdm_addr=tdm_addr, tdm_port=tdm_port,
                         password=password,
                         debug=debug)
    node = await client.wait_for_node(**kwargs)
    await node.lock()

    global _interactive_console
    _interactive_console = TDMConsole(local_var=get_ipython().user_ns)
    await _interactive_console.init(client, node)

    # configure ipython
    ip = get_ipython()

    ip.events.register("pre_run_cell", _pre_run_cell)
    ip.events.register("post_run_cell", _post_run_cell)

async def stop():
    """Stop the connection with the Thymio and variable synchronization.
    """

    # undo ipython configuration
    ip = get_ipython()
    ip.events.unregister("pre_run_cell", _pre_run_cell)
    ip.events.unregister("post_run_cell", _post_run_cell)

    # disconnect node, tdm and zeroconf
    global _interactive_console
    await _interactive_console.node.unlock()
    _interactive_console.client.disconnect()
    _interactive_console.client.close()
    _interactive_console = None

def get_client():
    """Get the ClientAsync object.
    """
    return _interactive_console.client if _interactive_console else None

def get_node():
    """Get the ClientAsyncCacheNode object.
    """
    return _interactive_console.node if _interactive_console else None

def tdm_properties():
    """Get the TDM address (string) and TCP port (number), or None if not
    available.
    """

    if _interactive_console is None or _interactive_console.client is None:
        return None, None
    return (_interactive_console.client.tdm_addr,
            _interactive_console.client.tdm_port)

def list_robots(robot_id=None, robot_name=None):
    """List the robots known to tdmclient without waiting.

    Arguments:
        robot_id - robot node id (default: any)
        robot_name - robot name (default: any)
    """
    if _interactive_console is None or _interactive_console.client is None:
        return []
    _interactive_console.client.process_waiting_messages()
    return list(_interactive_console.client.filter_nodes(_interactive_console.client.nodes,
                                                         node_id=robot_id,
                                                         node_name=robot_name))

def sync_var(func):
    # candidate variables to sync: globals referenced in func
    candidates = set(func.__code__.co_names)

    def func_wrapper(*args, **kwargs):
        node = get_node()
        vars_to_sync = candidates & {_interactive_console.to_python_name(name) for name in node.var.keys()}
        _interactive_console.fetch_variables(vars_to_sync)
        r = func(*args, **kwargs)
        _interactive_console.send_variables(vars_to_sync)
        return r

    # make a copy of wrapper and change its default args to match func
    import types, functools
    w = types.FunctionType(code=func_wrapper.__code__, globals=func_wrapper.__globals__, name=func.__name__, closure=func_wrapper.__closure__)
    functools.update_wrapper(w, func)
    return w

def process_events(on_event_data, *, all_nodes=False):
    """Listen to events sent by the program running on the robot and process
    them until _exit is received.

    Argument:
        on_event_data -- func(node, event_name) called when new data is received

    Key argument:
        all_nodes -- True to get events from all robots,
                     False (default) to get events from default robot
    """

    try:
        _interactive_console.process_events(on_event_data=on_event_data,
                                            all_nodes=all_nodes)
    except KeyboardInterrupt:
        # avoid long exception message with stack trace
        print("Interrupted")

async def watch(timeout=-1,
                zeroconf=None, tdm_addr=None, tdm_port=None, password=None,
                robot_id=None, robot_name=None):
    """Display the robot variables with live updates until the timeout elapses
    or the execution is interrupted.

    Arguments:
        timeout -- amount of time until updates stop
        zeroconf -- True to use find TDM with zeroconf (default: automatic)
        password - TDM password (default: None, not necessary for local TDM)
        tdm_addr -- address of the tdm
        tdm_port -- port of the tdm
            (default: connection established by start(), or from zeroconf)
        robot_id ID -- robot specified by id (default: first robot)

        robot_name NAME -- robot specified by name (default: first robot)
    """

    import IPython.display

    def var_dict_to_md(variable_dict):
        md = "| Variable | Value |\n| --- | --- |\n"
        md += "\n".join([
            f"| {name} | {variable_dict[name]} |"
            for name in variable_dict
        ])
        return md

    async def watch_node(client, node):
        variable_dict = node.var

        def variables_changed_listener(node, variable_update_dict):
            nonlocal variable_dict
            variable_dict = dict(sorted({**variable_dict, **variable_update_dict}.items()))
            IPython.display.clear_output(wait=True)
            md = var_dict_to_md(variable_dict)
            IPython.display.display(IPython.display.Markdown(md))

        node.add_variables_changed_listener(variables_changed_listener)
        variables_changed_listener(node, node.var)
        try:
            await client.sleep()
        except:
            # avoid long exception message with stack trace
            print("Interrupted")
        finally:
            IPython.display.clear_output(wait=True)
            node.remove_variables_changed_listener(variables_changed_listener)

    if _interactive_console is not None:
        await watch_node(_interactive_console.client, _interactive_console.node)
    else:
        with ClientAsync(zeroconf=zeroconf,
                         tdm_addr=tdm_addr, tdm_port=tdm_port,
                         password=password) as client:
            await client.wait_for_status_set({ClientAsync.NODE_STATUS_AVAILABLE,
                                              ClientAsync.NODE_STATUS_BUSY})
            node = client.first_node(node_id=robot_id, node_name=robot_name)
            await node.watch(variables=True)
            await watch_node(client, node)

from IPython.core.magic import register_line_magic, register_cell_magic
import getopt
import sys
import shlex

@register_cell_magic
def run_python(line, cell):
    """Transpile the whole cell from Python to Aseba, send it to the robot and
    run it.

    Options:

        --clear-event-data: clear event data so that function get_event_data()
        doesn't include events from a previous run.

        --nothymio: don't import Thymio symbols (module "thymio" should be
        imported explicitly if needed).

        --robotid ID: run on robot specified by id.

        --robotname NAME: run on robot specified by name.

        --robotindex I: run on robot specified by index
                        (0=first=default, 1=second etc.)

        --wait: continue running to receive events from the robot and display
        --warning-missing-global: display warnings for local variables which
                                  hide global variables with the same name
        print output until exit() is called in the program or the execution
        is interrupted. Other events are stored and can be obtained with
        function get_event_data().
    """

    args = shlex.split(line)
    wait = False
    clear_event_data = False
    import_thymio = True
    warning_missing_global = False
    nodes = []

    try:
        arguments, values = getopt.getopt(args,
                                          "",
                                          [
                                              "clear-event-data",
                                              "nothymio",
                                              "robotid=",
                                              "robotindex=",
                                              "robotname=",
                                              "wait",
                                              "warning-missing-global",
                                          ])
    except getopt.error as err:
        print(str(err), file=sys.stderr)
        return
    for arg, val in arguments:
        if arg == "--clear-event-data":
            clear_event_data = True
        elif arg == "--nothymio":
            import_thymio = False
        elif arg == "--robotid":
            for id in val.split(","):
                node = _interactive_console.find_robot(robot_id=id)
                if node not in nodes:
                    nodes.append(node)
        elif arg == "--robotindex":
            for i in val.split(","):
                node = _interactive_console.find_robot(robot_index=int(i))
                if node not in nodes:
                    nodes.append(node)
        elif arg == "--robotname":
            for name in val.split(","):
                node = _interactive_console.find_robot(robot_name=name)
                if node not in nodes:
                    nodes.append(node)
        elif arg == "--wait":
            wait = True
        elif arg == "--warning-missing-global":
            warning_missing_global = True
    if len(values) > 0:
        print(f"Unexpected argument {values[0]}", file=sys.stderr)
        return

    if clear_event_data:
        _interactive_console.clear_event_data()

    try:
        _interactive_console.run_program(cell,
                                         nodes=nodes if len(nodes) > 0 else None,
                                         language="python",
                                         warning_missing_global=warning_missing_global,
                                         wait=wait, import_thymio=import_thymio)
    except KeyboardInterrupt:
        # avoid long exception message with stack trace
        print("Interrupted")

@register_cell_magic
def run_aseba(line, cell):
    """Send to the robot the whole cell as an Aseba program and run it.

    Options:

        --robotid ID: run on robot specified by id.

        --robotname NAME: run on robot specified by name.

        --robotindex I: run on robot specified by index
                        (0=first=default, 1=second etc.)
    """

    args = shlex.split(line)
    nodes = []
    try:
        arguments, values = getopt.getopt(args,
                                          "",
                                          [
                                              "robotid=",
                                              "robotindex=",
                                              "robotname=",
                                          ])
    except getopt.error as err:
        print(str(err), file=sys.stderr)
        return
    for arg, val in arguments:
        if arg == "--robotid":
            for id in val.split(","):
                node = _interactive_console.find_robot(robot_id=id)
                if node not in nodes:
                    nodes.append(node)
        elif arg == "--robotindex":
            for i in val.split(","):
                node = _interactive_console.find_robot(robot_index=int(i))
                if node not in nodes:
                    nodes.append(node)
        elif arg == "--robotname":
            for name in val.split(","):
                node = _interactive_console.find_robot(robot_name=name)
                if node not in nodes:
                    nodes.append(node)
    if len(values) > 0:
        print(f"Unexpected argument {values[0]}", file=sys.stderr)
        return

    _interactive_console.run_program(cell,
                                     nodes = nodes if len(nodes) > 0 else None,
                                     language="aseba")

@register_cell_magic
def transpile_to_aseba(line, cell):
    """Transpile the whole cell from Python to Aseba and display the result.

    Option:

        --nothymio: don't import Thymio symbols (module "thymio" should be
        imported explicitly if needed).
        --warning-missing-global: display warnings for local variables which
                                  hide global variables with the same name
    """

    args = shlex.split(line)
    import_thymio = True
    warning_missing_global = False

    try:
        arguments, values = getopt.getopt(args,
                                          "",
                                          [
                                              "nothymio",
                                              "warning-missing-global",
                                          ])
    except getopt.error as err:
        print(str(err), file=sys.stderr)
        return
    for arg, val in arguments:
        if arg == "--nothymio":
            import_thymio = False
        elif arg == "--warning-missing-global":
            warning_missing_global = True
    if len(values) > 0:
        print(f"Unexpected argument {values[0]}", file=sys.stderr)
        return

    transpiler = _interactive_console.transpile(cell,
                                                import_thymio=import_thymio,
                                                warning_missing_global=warning_missing_global)

    src_a = transpiler.get_output()
    print(src_a)
