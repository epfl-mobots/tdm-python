# Changelog

Notable changes of tdmclient. Release versions refer to [https://pypi.org/project/tdmclient/].

## [Unreleased]

### Added

- Arguments, return value and local variables in function definitions.
- New method Client.shutdown_tdm
- New callbacks Client.on_events_received, Client.on_event_received
- Argument of callback Client.on_variables_changed simplified

## [0.1.1] - 2021-03-25

### Added

- Python-to-Aseba transpiler.
- Node objects with significant refactoring.
    Node-related methods of classes `Thymio`, `Client` or `ClientAsync` which used `node_id_str` to identify the node have been replaced by methods of new classes `Node`, `ClientNode` and `ClientAsyncNode`, respectively. Their use is simpler.
- Options to specify the TDM address and port and avoid zeroconf

## [0.1.0] - 2021-03-17

### Added

- First release on PyPI.
