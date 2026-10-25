## ADDED Requirements

### Requirement: An error before the run reaches the run's output

When `robotcode` stops a run or debug session with an error of its own before Robot Framework runs, such as an error of the configuration, the error SHALL appear once in the run's output, with every console value: in the Debug Console with `internalConsole`, in the terminal with the others.

#### Scenario: Selected profile that does not exist, with the internal console

- **WHEN** the folder's `robotcode.profiles` names `typo`, which the folder's configuration does not define, and the user runs a test with `internalConsole`
- **THEN** the Debug Console shows `Error: No profile matches 'typo'.` once, and the session ends

#### Scenario: Invalid value in robot.toml, with the internal console

- **WHEN** the folder's `robot.toml` sets `output-dir = 5` and the user runs a test with `internalConsole`
- **THEN** the Debug Console shows the error about `output-dir` once, and the session ends

#### Scenario: Run terminal

- **WHEN** such an error stops a run with `robotcodeTerminal`
- **THEN** the run terminal shows the error once
