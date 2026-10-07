# Spec Delta: keyword-documentation-rendering

## ADDED Requirements

### Requirement: Completion details of a variable file show its variables

When an item of the completion of a `Variables` import names a variable file or a module, its details SHALL show the documentation that the hover of a `Variables` import of that file or module shows: the heading `Variables <name>` and its variables with their values, as loading it without arguments yields them. The details SHALL NOT show the file or module as a library. Folders get no details, as before.

#### Scenario: Python variable file
- **WHEN** `vars.py` defines `HOST = "localhost"` and `PORT = 8270`, the completion of `Variables    ` offers `vars.py`, and the item is resolved
- **THEN** the details show the heading `Variables vars` and the variables `${HOST}` with `localhost` and `${PORT}` with `${8270}`
- **AND** they show no `Library` heading and no introduction from the module docstring

#### Scenario: YAML variable file
- **WHEN** `settings.yaml` contains `user: alice` and `timeout: 5 s`, and its item in the completion of `Variables    ` is resolved
- **THEN** the details show the heading `Variables settings` and the variables `${user}` and `${timeout}` with their values

### Requirement: Completion details of a variable file that fails to load

When loading the variable file or module of an item of the completion of a `Variables` import without arguments fails, the item's details SHALL show the heading and the error that loading reported.

#### Scenario: Variable file that needs arguments
- **WHEN** `needsarg.py` defines `def get_variables(env)`, and its item in the completion of `Variables    ` is resolved
- **THEN** the details show the heading `Variables needsarg` and the error that loading it without arguments reported, on Robot Framework 7.5 `Variable file expected 1 argument, got 0.`
