# This file is part of tdmclient.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import setup

with open("help.md", "r") as fh:
    long_description = fh.read()

setup(
    name='tdmclient',
    version='0.1.0',
    author='Yves Piguet',
    packages=['tdmclient'],
    description='Communication with Thymio II robot via the Thymio Device Manager',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/epfl-mobots/tdm-python',
    install_requires=[
        "zeroconf",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Education",
    ],
    python_requires='>=3.6',
)
