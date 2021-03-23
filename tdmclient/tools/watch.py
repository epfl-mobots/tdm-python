# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import ClientAsync

if __name__ == "__main__":

    with ClientAsync(debug=2) as client:

        async def prog():
            await client.wait_for_node()
            node = client.first_node()
            await node.watch(flags=0x3f)  # all
            await client.sleep()

        client.run_async_program(prog)
