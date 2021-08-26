"""Equivalent of repl for Jupyter notebooks.
"""

_interactive_console = None
from tdmclient import ClientAsync, TDMConsole

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

    def pre_run_cell(info):
        _interactive_console.pre_run(info.raw_cell)

    def post_run_cell(_):
        _interactive_console.post_run()

    ip.events.register("pre_run_cell", pre_run_cell)
    ip.events.register("post_run_cell", post_run_cell)

# define functions in tdmclient.notebook

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
