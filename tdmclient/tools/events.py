# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ClientAsync

if __name__ == "__main__":

    with ClientAsync(debug=2) as client:

        thymio_program = """
leds.top = [0, 0, 32]
leds.bottom.left = [32, 0, 0]
leds.bottom.right = [0, 32, 0]
timer.period[0] = 1000

onevent timer0
    emit e0
    emit e2 [1, 23]
"""

        async def prog():
            with await client.lock() as node_id_str:
                error = await client.register_events(node_id_str, [
                    ("e0", 0),
                    ("e2", 2),
                ])
                error = await client.compile(node_id_str, thymio_program)
                if error is not None:
                    print(f"Compilation error: {error['error_msg']}")
                else:
                    await client.watch(node_id_str, events=True)
                    error = await client.run(node_id_str)
                    if error is not None:
                        print(f"Error {error['error_code']}")
                await client.sleep(10)
            print("done")

        client.run_async_program(prog)
