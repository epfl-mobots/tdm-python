# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from tdmclient import Server, ServerNode, ThymioFB

if __name__ == "__main__":

    server = Server()
    server.nodes.add(ServerNode(type=ThymioFB.NODE_TYPE_THYMIO2,
                                variables={
                                    "a": [123],
                                    "b": [4, 5, 6],
                                }))
    server.start()
    while True:
        server.accept()
