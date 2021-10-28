# TDM client Python module

Python module to connect to the Thymio Device Manager (TDM), the part of Thymio Suite responsible for managing connections to one or several [Thymio II robots](https://thymio.org): robot discovery, description, events, observation or change of variables, and program compilation, loading and execution.

Clients connect via TCP sockets or WebSockets and exchange packets encoded with FlatBuffer and FlexBuffer. The TCP port is advertised with zeroconf. This module uses (or will use) TCP and its own implementation of FlatBuffer/FlexBuffer.

The TDM connects to the robots via USB cable(s), one per robot, or USB RF dongle(s), potentially with multiple robots per dongle. The communication protocol is also based on the exchange of packets, but at a lower level. For instance, packet size is restricted and often requires message fragmentation, and programs must be compiled to bytecode while the TDM includes a compiler for the Aseba language. The TDM also allows multiple clients to connect simultaneously to the same robot(s), for example to let a teacher observe the programs executed by their pupils. Python module [thymiodirect](https://pypi.org/project/thymiodirect/) provides a direct connection without the TDM.

To install the latest release from [https://pypi.org]:
```
python3 -m pip install --upgrade tdmclient
```

To install the current development version from this github repository:
```
python3 -m pip install git+https://github.com/epfl-mobots/tdm-python
```
