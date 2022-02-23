
## Python repl in Mu

Mu is a "Python code editor for beginner programmers". Its web site is [https://codewith.mu](https://codewith.mu).

Mu has multiple _modes_, including Python 3 with a repl based on Jupyter QtConsole. Hence it supports the tdmclient package out of the box.

To select the Python 3 mode, click the Mode button (the leftmost button) and select Python 3. Then click the REPL button to display the Jupyter console in a panel. You can use magic commands like in a Jupyter notebook. Type
```
%pip install --upgrade --quiet tdmclient
```

You can just hit the Return key to execute the command; no need to hold down the Shift key. Then restart the Python kernel by clicking twice the REPL button, once to close the panel and once to reopen it.

Once tdmclient is installed, you can import the notebook methods and connect to a robot:
```
import tdmclient.notebook
await tdmclient.notebook.start()
```

To switch the top LED to cyan:
```
leds_top = [0, 32, 32]
```
