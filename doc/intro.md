
# tdmclient

Python package to connect to a [Thymio II robot](https://thymio.org) via the Thymio Device Manager (TDM), a component of the Thymio Suite. The connection between Python and the TDM is done over TCP to the port number advertised by zeroconf. Simple Python programs can run directly on the Thymio thanks to a transpiler.

## Introduction

There are basically three ways to use tdmclient. From easy to more advanced:

- If there is no need to communicate with the robot while the program runs, or if it's limited to messages and values displayed by the function `print()`, Python programs in .py files can be run on the Thymio with the following terminal command:

    ```
    python3 -m tdmclient.tools.run program.py
    ```

    The program is converted from Python to Aseba, the main programming language of the Thymio. The Thymio microcontroller has very limited processing power and memory; only a small part of Python is supported. For more information, see section [Python-to-Aseba transpiler](#Python-to-Aseba_transpiler).

    Instead of a terminal window, you can run Python programs from the simple programming environment [Thonny](https://thonny.org/) with the plug-in [tdmclient-ty](https://pypi.org/project/tdmclient-ty/).

    In a terminal, tdmclient offers other tools to list robots, watch the Thymio internal variables, etc. They're described in section [Tools](#Tools).

- Jupyter is a programming environment based on documents which contain text, executable code, graphics, etc. called _notebooks_ (ipynb files). Specific support for Jupyter is provided by tdmclient to interact directly with Thymio variables, embed Thymio programs in Python, run them, display results, and exchange data between the robot and the computer to benefit from the strengths of both: the Thymio for very reactive code close to its sensors and actuators, and your computer for its much more powerful processing capabilities, the complete Python language and ecosystem, graphics and user interface, files, the Internet... You can also control multiple robots.

    In Jupyter notebooks, the most basic way to execute Python code is one statement at a time. This is also possible directly with Python itself, without Jupyter, with what is known as _repl_ (read-eval-print loop): Python reads the statement you type, it evaluates it when you hit the Return key, it prints the result, and it loops by prompting you for more. The tdmclient module can also be used at that level, where the internal Thymio variables (leds, proximity sensors, motors...) are synchronized with Python and you have a direct access to them as if you were running the repl directly on the robot. You can also create Python programs running on the Thymio from the repl. This is explained in section [Python repl for Thymio](#Python_repl_for_Thymio).

- With `Client` and `Node` objects. `Client` is the base Python class for objects which manage the connection between your Python program and Thymio Suite, or more specifically the Thymio Device Manager (tdm), the part involved with the communication with the robots. `Node` is the base Python class for objects which are the counterpart of robots on the other side of the connection. Controlling robots with these objects is described in section [tdmclient classes and objects](#tdmclient_classes_and_objects).

The package available on [pypi.org](https://pypi.org/project/tdmclient/), which can be installed with `pip`, contains just tdmclient and its documentation. The [Github code repository](https://github.com/epfl-mobots/tdm-python) also contains [Jupyter notebooks](https://github.com/epfl-mobots/tdm-python/tree/main/notebooks) (begin with [intro.ipynb](https://github.com/epfl-mobots/tdm-python/blob/main/notebooks/intro.ipynb)) and examples of [programs for the Thymio](https://github.com/epfl-mobots/tdm-python/tree/main/examples/robot) to run with `tdmclient.tools.run`.
