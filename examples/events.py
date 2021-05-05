# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ClientAsync

if __name__ == "__main__":

    with ClientAsync() as client:

        def on_event_received(node, event_name, event_data):
            print(event_name, event_data)

        client.add_event_received_listener(on_event_received)

        thymio_program = """
var i = 0
leds.top = [0, 0, 32]
leds.bottom.left = [32, 0, 0]
leds.bottom.right = [0, 32, 0]
timer.period[0] = 500

onevent timer0
    emit e0
    emit e2 [123, i]
    i++
"""

        async def prog():
            with await client.lock() as node:
                error = await node.register_events([
                    ("e0", 0),
                    ("e2", 2),
                ])
                error = await node.compile(thymio_program)
                if error is not None:
                    print(f"Compilation error: {error['error_msg']}")
                else:
                    await node.watch(events=True)
                    error = await node.run()
                    if error is not None:
                        print(f"Error {error['error_code']}")
                await client.sleep(10)
            print("done")

        client.run_async_program(prog)
