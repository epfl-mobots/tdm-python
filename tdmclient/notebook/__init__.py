"""Equivalent of repl for Jupyter notebooks.
"""

_interactive_console = None

async def thymio_sync(tdm_addr = None, tdm_port = None):

    from tdmclient import ClientAsync, TDMConsole

    client = ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port)
    node = await client.wait_for_node()
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

from IPython.core.magic import register_line_magic, register_cell_magic
@register_cell_magic
def run_python(line, cell):
    _interactive_console.run_program(cell, "python")

from IPython.core.magic import register_line_magic, register_cell_magic
@register_cell_magic
def run_aseba(line, cell):
    _interactive_console.run_program(cell, "aseba")

from IPython.core.magic import register_line_magic, register_cell_magic
@register_cell_magic
def transpile_to_aseba(line, cell):
    from tdmclient.atranspiler import ATranspiler
    src_a = ATranspiler.simple_transpile(cell)
    print(src_a)
