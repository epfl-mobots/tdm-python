
## Tools

Connect a robot to your computer via a USB cable or the RF dongle and launch Thymio Suite. In Thymio Suite, you can click the Aseba Studio icon to check that the Thymio is recognized, and, also optionally, start Aseba Studio (select the robot and click the button "Program with Aseba Studio"). Only one client can control the robot at the same time to change a variable or run a program. If that's what you want to do from Python, either don't start Aseba Studio or unlock the robot by clicking the little lock icon in the tab title near the top left corner of the Aseba Studio window.

Some features of the library can be accessed directly from the command window by typing `python3 -m tdmclient.tools.abc arguments`, where `abc` is the name of the tool.

### tdmclient.tools.tdmdiscovery

Display the address and port of TDM advertised by zeroconf until control-C is typed:
```
python3 -m tdmclient.tools.tdmdiscovery
```

### tdmclient.tools.list

Display the list of nodes with their id, group id, name, status, capability, and firmware version:
```
python3 -m tdmclient.tools.list
```

Display options:
```
python3 -m tdmclient.tools.list --help
```

### tdmclient.tools.run

Run an Aseba program on the first Thymio II robot and store it into the scratchpad so that it's seen in Aseba Studio:
```
python3 -m tdmclient.tools.run --scratchpad examples/blink.aseba
```

Stop the program:
```
python3 -m tdmclient.tools.run --stop
```

To avoid having to learn the Aseba language, a small subset of Python can also be used:
```
python3 -m tdmclient.tools.run --scratchpad examples/blink.py
```

The `print` statement, with scalar numbers and constant strings, is supported. Work is shared between the robot and the PC.
```
python3 -m tdmclient.tools.run --scratchpad examples/print.py
```

Display other options:
```
python3 -m tdmclient.tools.run --help
```

### tdmclient.tools.watch

Display all node changes (variables, events and program in the scratchpad) until control-C is typed:
```
python3 -m tdmclient.tools.watch
```

### tdmclient.tools.gui

Run the variable browser in a window. The GUI is implemented with TK.
```
python3 -m tdmclient.tools.gui
```

At launch, the robot is unlocked, i.e. the variables are just fetched and displayed: _Observe_ is displayed in the status area at the bottom of the window. To be able to change them, activate menu Robot>Control. Then you can click any variable, change its value and type Return to confirm or Esc to cancel.
