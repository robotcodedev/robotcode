# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: Problems are reported before a run

While a Robot Framework run configuration is edited and when it is started, the plugin SHALL report these problems in addition to PyCharm's own check of the interpreter, which it SHALL NOT repeat:

- an error when RobotCode's environment check found the configuration's interpreter not usable, with the message of the result and a fix that opens the Python Interpreter settings;
- a warning when the last check of the configuration's interpreter failed.

#### Scenario: Interpreter without Robot Framework

- **WHEN** a configuration's interpreter was checked and has no Robot Framework, and the user starts the configuration
- **THEN** no robot process starts, the IDE shows the configuration with the error that Robot Framework is not installed, and its fix opens the Python Interpreter settings

#### Scenario: No interpreter

- **WHEN** a configuration has no Python interpreter
- **THEN** the editor shows PyCharm's own error about the missing interpreter, and no second error from RobotCode about it

### Requirement: Remote interpreters are reported before a run

While a Robot Framework run configuration is edited and when it is started, the plugin SHALL report an error when the configuration's interpreter is a remote one, which Robot Framework runs do not support yet.

#### Scenario: Remote interpreter

- **WHEN** a configuration's interpreter is a WSL, Docker or SSH interpreter
- **THEN** the editor shows the error that Robot Framework runs with remote interpreters are not supported yet, before the configuration is run

### Requirement: Problems of the run target are reported before a run

While a Robot Framework run configuration is edited and when it is started, the plugin SHALL report an error that names each path of a "Files and folders" target that does not exist, and a warning that names the items of a "Tests and suites" target that the current discovery does not contain, when discovery has a result.

#### Scenario: Path that does not exist

- **WHEN** the target is "Files and folders" with `tests/gone.robot`, which does not exist, and the user starts the configuration
- **THEN** no robot process starts, and the error names `tests/gone.robot`

#### Scenario: Renamed test

- **WHEN** the target is "Tests and suites" with an item whose test has been renamed, and discovery has a result
- **THEN** the editor shows a warning that names the item, and the configuration can still be started

### Requirement: How the problems of a run configuration are checked

An error about a run configuration SHALL keep the run from starting; a warning SHALL NOT. The validation SHALL use only results of the environment check that already exist, and SHALL NOT start a Python process while the IDE waits for it. When no result exists for the configuration's interpreter, it SHALL request a check in the background and report nothing about the interpreter.

#### Scenario: Interpreter not checked yet

- **WHEN** a configuration uses an interpreter that RobotCode has not checked yet, and the user opens the configuration in the editor
- **THEN** the editor opens without delay and reports nothing about the interpreter, and a check of it starts in the background
