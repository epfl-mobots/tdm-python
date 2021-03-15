#!/usr/bin/env python3
# Yves Piguet, Jan-Feb 2021

from tdmclient import ClientAsync

if __name__ == "__main__":

    with ClientAsync(debug=0) as client:

        thymio_program = """
leds.top = [0, 0, 32]
leds.bottom.left = [32, 0, 0]
leds.bottom.right = [0, 32, 0]
"""

        async def prog():
            with await client.lock() as node_id_str:
                error = await client.compile(node_id_str, thymio_program)
                if error is not None:
                    print(f"Compilation error: {error['error_msg']}")
                else:
                    error = await client.run(node_id_str)
                    if error is not None:
                        print(f"Error {error['error_code']}")
            print("done")

        client.run_async_program(prog)
