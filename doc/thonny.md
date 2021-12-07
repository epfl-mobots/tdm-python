
## Python repl in Thonny

Thonny is a "Python IDE for beginners". Its web site is [https://thonny.org](https://thonny.org).

Thonny runs a standard Python distribution. Hence it supports the tdmclient package out of the box.

If you just want to run Python programs on the robot, the _tdmclient-ty_ plug-in adds commands to the Tools menu. To install it, select the menu Tools>Manage plug-ins, type _tdmclient-ty_ in the search box, and click button _Search on PyPI_. Click the link _tdmclient-ty_ in the result list (normally the first result), then the Install button below.

For complete access to _tdmclient_, here are two tricks you might find useful.
- To make sure you install tdmclient for the Python environment used by Thonny, select the menu Tools>Manage packages, type _tdmclient_ in the search box, and click button _Search on PyPI_. Click the link _tdmclient_ in the result list (normally the only result), then the Install button below.
- To run the repl in Thonny's shell, you can launch it with the code of `tdmclient.tools.repl`:
    ```
    import tdmclient.tools.repl
    tdmclient.tools.repl.main()
    ```
