#!/usr/bin/env python3

# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ClientAsync

if __name__ == "__main__":

    with ClientAsync(debug=0) as client:

        thymio_program = """
leds.top = [0, 0, 32]
leds.bottom.left = [32, 0, 0]
leds.bottom.right = [0, 32, 0]
"""

        async def prog():
            with await client.lock() as node:
                print(node)
                error = await node.compile(thymio_program)
                if error is not None:
                    print(f"Compilation error: {error['error_msg']}")
                else:
                    error = await node.run()
                    if error is not None:
                        print(f"Error {error['error_code']}")
            print("done")

        client.run_async_program(prog)
