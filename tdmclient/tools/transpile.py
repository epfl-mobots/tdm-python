# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

import sys
from tdmclient.atranspiler import ATranspiler

if __name__ == "__main__":

    src = None
    if len(sys.argv) >= 2:
        with open(sys.argv[1]) as f:
            src = f.read()
    else:
        src = sys.stdin.read()

    output_src = ATranspiler.simple_transpile(src)
    print(output_src)
