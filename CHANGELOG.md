# Changelog

Notable changes of tdmclient. Release versions refer to [https://pypi.org/project/tdmclient/].

## [Unreleased]

### Added

- In transpiler:
    - In `tdmclient.tools.transpile` and notebooks, option `--warning-missing-global` to display warnings for local variables which hide global variables (a declaration as global could be missing)
    - Exception `NameError` replaced by `TranspilerError` with node context to display the line number in the error message
    - Property `lineno` in exception class `TranspilerError`
    - Transpiler exception for unsupported augmented assignments `/=`, `**=` and `@=`
    - Errors on undefined variables or invalid use of list variables or indexing in augmented assignments
- In function `ClientAsync.wait_for_node`, optional argument `timeout`
- In `tdmclient.tools.server`:
    - option `--port`
    - support for WebSocket

### Fixed

- In transpiler:
    - Name of local list variables passed to native functions wasn't converted
    - User functions called in arguments of `emit`, `exit` and `print` caused an exception
- In server:
	- Clean shutdown of connection thread
	- Socket address reused
	- Separate group id

## [0.1.14] - 2022-01-23

### Added

- Transpiler exception for unsupported operators such as `/`, `**` and `@`

### Fixed

- Options of tool `tdmclient.tools.gui`
- In transpiler:
    - Check that constants such as `RED` are not assigned to (clean error from transpiler instead of incorrect transpiled code)
    - When auxiliary statements are required to compute the condition of `elif`, the generated code is `else aux if ... end end` instead of `aux elseif ... end`

## [0.1.13] - 2022-01-11

### Added

- Optional boolean argument `zeroconf` in `Client` constructor and Jupyter functions `start()`, `list()`, and `watch()`
- Class `NodeLockError` with the current node status raised when a node cannot be locked
- Optional key argument `password` in the constructor of `ClientAsync` to connect to remote TDM
- In repl:
	- Key argument `robot_index` in functions and option `--robotindex` in Jupyter magic commands to specify the robot by index
	- Optional robot specification in `send_event`
	- Optional argument `all_nodes` in function `process_events`
- In notebooks:
	- Optional `debug` argument in `start()`
	- Optional `password` argument in `start()`, `list()`, `watch()`
	- Optional `timeout` argument in `list()` and `get_nodes()`
	- Multiple targets in magic commands `%%run_python` and `%%run_aseba` with comma-separated list of robots
- Option `--password` in tools `tdmclient.tools.guy`, `tdmclient.tools.list`, `tdmclient.tools.repl`, `tdmclient.tools.run`, `tdmclient.tools.watch`

### Changed

- In repl and Jupyter, callback `on_event_data` has a new `node` argument to better support interaction with multiple robots

### Fixed

- Method `Client.create_node()` referred to a symbol which wasn't imported
- Watch flag changes sent by methods `ClientAsyncNode.watch` and `ClientAsyncNode.unwatch`
- In repl, support for starred expressions
- Support for fragmented packets
- In notebooks, function `get_nodes()` must be called after `start()` and with its tdm connection to avoid returning orphan nodes

## [0.1.12] - 2021-12-07

### Added

- In `tdmclient.tools.watch`, options to select the tdm and the robot
- In repl:
	- in functions `run()` and `stop()`, keyword arguments `robot_id` or `robot_name` to specify another robot, which is locked during the call
	- the complete Python or Aseba source code of a program can be passed to function `run()` as an alternative to collecting @onevent functions and global variables
- In notebooks:
	- private symbols not defined anymore in `tdmclient.notebook`
	- docstrings for magic commands, displayed with e.g. `%%run_python?`
	- In magic commands `%%run_python` and `%%run_aseba`, options `--robot-id ID` or `--robot-name NAME` to specify another robot, which is locked during the execution
	- functions `list()` and `get_nodes()` can be called before `start()`
	- function `tdmclient.notebook.watch()`, to be called as `await tdmclient.notebook.watch()` to display the robot variables with live update
- In transpiler, support for lists given as `len(...)*[...]` or `[...]*len(...)`
- When decoding flatbuffer strings, illegal utf-8 sequences decoded as `U+FFFD` (replacement character) instead of raising an exception

### Changed

- In notebooks, functions `list()` and `get_nodes()` use by default the TDM connection established by `start()` instead of a local TDM advertized by zeroconf

### Fixed

- Local variables defined by the assignment of a global variable neither declared with `global` nor predefined as Thymio variables raised an exception

## [0.1.11] - 2021-11-17

### Added

- Runtime VM errors reported in repl and `tdmclient.tools.run`

### Fixed

- In transpiler, temporary variables in `for` loops overwrote the loop limit and step
- Format of the tdm message for VM state changed

## [0.1.10] - 2021-11-04

### Added

- In transpiler, support for lists given as `num*[...]` or `[...]*num`

### Fixed

- In transpiler, access to undeclared global variables when they aren't hidden by a local variable
- In repl and notebooks, synchronized user variables not forgotten when a program is run on the robot

## [0.1.9] - 2021-10-20

### Added

- In `tdmclient.tools.repl`, launch code moved to a function `main(argv=None)` so that it can be called from the Python shell
- In repl and notebooks, shortened message when interrupting program

### Fixed

- In transpiler, module "clock" fixed
- In repl, better support for Python 3.6 and 3.10

## [0.1.8] - 2021-10-13

### Added

- In transpiler:
	- module `clock` with functions `seconds()`, `ticks_50Hz()` and `reset()`
- In repl:
	- functions `get_client()` and `get_node()`
	- functions `get_var` and `set_var`
	- global variables defined in the robot program added to the list of variables to be synchronized
- In notebooks:
	- functions `get_nodes()` and `list()` to get the list of nodes available in the TDM
	- decorator `@sync_var` to synchronize the robot variables accessed in the function
	- in `%%run_python`, option `--clear-event-data` to call `clear_event_data()` before starting the program

### Fixed

- In the `run()` function of repl and notebooks and in `tdmclient.tools.run`, the decision to wait or not when no explicit option is specified is now based only on custom events (events not predefined in the vm)
- Better compatibility with Python 3.6:
	- in transpiler, support of string constants as documentation strings or arguments of `print()` and `emit()`
	- in repl, no warning for numbers and booleans
- Decoding of the size of array variables obtained from TDM
- In repl, underscores not converted to dots in name of global variables which don't correspond to a known Thymio variable
- Documentation improvements

## [0.1.7] - 2021-09-27

### Added

- In transpiler, support for receiving custom events with arguments
- In repl, function `send_event`
- In notebooks, functions `stop`, `get_client`, `get_node`

### Fixed

- In transpiler:
	- `%` in print string constants
	- in method `simple_transpile`, symbols from module `thymio` imported by default

## [0.1.6] - 2021-09-22

### Added

- In transpiler, definitions for more native functions
- New notebook to illustrate the use of native functions
- Nul bytes in zeroconf property "ws-port" discarded

## [0.1.5] - 2021-09-14

### Added

- In transpiler:
    - support for `exit`
    - dict of events emitted by `emit`, with automatic declaration by tool `tdmclient.tools.run` and function `run` in repl and notebooks
- In documentation:
    - note on the replacement of `run_async_program` with `await` in Jupyter notebooks
- By default, locking the default node raises an error if it's busy instead of waiting
- Event output in tool `tdmclient.tools.run` written with CSV format

### Fixed

- In transpiler:
    - `and` and `or`
    - augmented assignments with indexed variable target
    - `range` with negative step
    - list arguments in native function calls
    - check for recursive function calls
    - code generated for functions `math_clamp` and `math_muldiv`
- In repl, event listeners reset when needed

## [0.1.4] - 2021-08-30

### Added

- In transpiler:
    - support for `print`
    - support for module `thymio` which can replace predefined Thymio variables and native functions
- In tdmclient.tools.run, support for events

### Fixed

- In transpiler:
    - native functions without return value

## [0.1.3] - 2021-05-06

### Added

- Support for Jupyter notebooks
- In repl:
    - access to Aseba code
    - function to forget definitions for the Thymio
    - help and documentation
- In tools `gui`, `repl` and `run`, new options `--robotid` and `--robotid`

### Fixed

- In transpiler:
    - decoding of indices
    - compatibility with older versions
- In repl:
    - user-defined functions
    - initialization of global variables in robot code
- Tool `tdmclient.tools.variables` renamed `tdmclient.tools.gui`

## [0.1.2] - 2021-04-27

### Added

- In transpiler:
    - arguments, return value and local variables in function definitions;
    - dot replaced with underscore in Thymio variable and native function names;
    - Thymio variables must be declared as global in all function definitions;
    - conditional expressions;
    - chained comparisons;
    - function `len`;
    - better error messages
- New methods Client.shutdown_tdm, ClientAsync.rename, ClientAsync.send_events
- New callbacks Client.on_events_received, Client.on_event_received
- Argument of callback Client.on_variables_changed simplified
- Dummy server

### Fixed

- Missing tools in binary distribution

## [0.1.1] - 2021-03-25

### Added

- Python-to-Aseba transpiler.
- Node objects with significant refactoring.
    Node-related methods of classes `Thymio`, `Client` or `ClientAsync` which used `node_id_str` to identify the node have been replaced by methods of new classes `Node`, `ClientNode` and `ClientAsyncNode`, respectively. Their use is simpler.
- Options to specify the TDM address and port and avoid zeroconf

## [0.1.0] - 2021-03-17

### Added

- First release on PyPI.
