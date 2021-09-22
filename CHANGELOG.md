# Changelog

Notable changes of tdmclient. Release versions refer to [https://pypi.org/project/tdmclient/].

## [Unreleased]

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

# Fixed

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
