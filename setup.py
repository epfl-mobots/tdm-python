# This file is part of tdmclient.
# Copyright 2021-2022 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import setup

long_description = ""
for filename in [
                    "intro.md",
                    "install.md",
                    "tools.md",
                    "transpiler.md",
                    "repl.md",
                    "notebooks.md",
                    "lowlevel.md",
                ]:
    with open("doc/" + filename, "r") as f:
        long_description += f.read()

setup(
    name="tdmclient",
    version="0.1.14",
    author="Yves Piguet",
    packages=["tdmclient", "tdmclient.tools", "tdmclient.notebook", ],
    description="Communication with Thymio II robot via the Thymio Device Manager",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/epfl-mobots/tdm-python",
    install_requires=[
        "zeroconf",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Education",
    ],
    python_requires=">=3.6",
)
