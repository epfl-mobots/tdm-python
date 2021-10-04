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

async def get_nodes(tdm_addr=None, tdm_port=None, robot_id=None, robot_name=None):
    """Get a list of all the robots.

    Arguments:
        tdm_addr - TDM address as a string (default: localhost)
        tdm_port - TDM TCP port number (default: provided by zeroconf)
        robot_id - robot id to restrict the output (default: any)
        robot_name - robot name to restrict the output (default: any)
    """

    with ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port) as client:

        for _ in range(50):
            client.process_waiting_messages()
            if len(client.nodes) > 0:
                break
            await client.sleep(0.1)

        nodes = builtins.list(client.filter_nodes(client.nodes,
                                                  node_id=robot_id,
                                                  node_name=robot_name))

    return nodes

async def list(tdm_addr=None, tdm_port=None, robot_id=None, robot_name=None):
    """Display a list of all the robots.

    Arguments:
        tdm_addr - TDM address as a string (default: localhost)
        tdm_port - TDM TCP port number (default: provided by zeroconf)
        robot_id - robot id to restrict the output (default: any)
        robot_name - robot name to restrict the output (default: any)
    """

    with ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port) as client:

        for _ in range(50):
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

async def start(tdm_addr=None, tdm_port=None, **kwargs):
    """Start the connection with the Thymio and variable synchronization.

    Arguments:
        tdm_addr - TDM address as a string (default: localhost)
        tdm_port - TDM TCP port number (default: provided by zeroconf)
        node_id - robot node id (default: any)
        node_name - robot name (default: any)
    """

    client = ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port)
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

def list_robots(**kwargs):
    """List connected robots.

    Arguments:
        node_id - robot node id (default: any)
        node_name - robot name (default: any)
    """
    if _interactive_console is None or _interactive_console.client is None:
        return []
    _interactive_console.client.process_waiting_messages()
    return list(_interactive_console.client.filter_nodes(_interactive_console.client.nodes, **kwargs))

from IPython.core.magic import register_line_magic, register_cell_magic

@register_cell_magic
def run_python(line, cell):
    args = line.split()
    wait = "--wait" in args
    import_thymio = "--nothymio" not in args
    _interactive_console.run_program(cell, "python", wait=wait, import_thymio=import_thymio)

@register_cell_magic
def run_aseba(line, cell):
    _interactive_console.run_program(cell, "aseba")

@register_cell_magic
def transpile_to_aseba(line, cell):
    args = line.split()
    import_thymio = "--nothymio" not in args
    transpiler = _interactive_console.transpile(cell, import_thymio=import_thymio)
    src_a = transpiler.get_output()
    print(src_a)
