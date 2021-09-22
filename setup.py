# This file is part of tdmclient.
# Copyright 2021 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import setup

with open("doc/help.md", "r") as f:
    long_description = f.read()
with open("doc/transpiler.md", "r") as f:
    long_description += f.read()
with open("doc/repl.md", "r") as f:
    long_description += f.read()
with open("doc/notebooks.md", "r") as f:
    long_description += f.read()

setup(
    name="tdmclient",
    version="0.1.6",
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
