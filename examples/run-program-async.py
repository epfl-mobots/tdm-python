#!/usr/bin/env python3
# Yves Piguet, Jan-Feb 2021

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from tdmclient import ClientAsync

if __name__ == "__main__":

    with ClientAsync(debug=0) as client:

        thymio_program = """
leds.top = [0, 0, 32]
leds.bottom.left = [32, 0, 0]
leds.bottom.right = [0, 32, 0]
"""

        async def prog():
            await client.wait_for_status(client.NODE_STATUS_AVAILABLE)
            node_id_str = client.first_node()["node_id_str"]
            print(node_id_str)
            await client.lock_node(node_id_str)
            await client.wait_for_status(client.NODE_STATUS_READY)
            error = await client.compile(node_id_str, thymio_program)
            if error is not None:
                print(f"Compilation error: {error['error_msg']}")
            else:
                error = await client.run(node_id_str)
                if error is not None:
                    print(f"Error {error['error_code']}")
            await client.unlock_node(node_id_str)
            print("done")

        client.run_async_program(prog)
