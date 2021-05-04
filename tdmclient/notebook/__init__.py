"""Equivalent of repl for Jupyter notebooks.
"""

async def thymio_sync(tdm_addr = None, tdm_port = None):

    from tdmclient import ClientAsync, TDMConsole

    client = ClientAsync(tdm_addr=tdm_addr, tdm_port=tdm_port)
    node = await client.wait_for_node()
    await node.lock()

    interactive_console = TDMConsole(local_var=get_ipython().user_ns)
    await interactive_console.init(client, node)

    # configure ipython
    ip = get_ipython()

    def pre_run_cell(info):
        interactive_console.pre_run(info.raw_cell)

    def post_run_cell(_):
        interactive_console.post_run()

    ip.events.register("pre_run_cell", pre_run_cell)
    ip.events.register("post_run_cell", post_run_cell)

    return interactive_console
