# Changelog

Notable changes of tdmclient. Release versions refer to [https://pypi.org/project/tdmclient/].

## [Unreleased]

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
