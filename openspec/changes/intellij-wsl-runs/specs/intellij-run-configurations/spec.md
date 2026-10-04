# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: Runs inside the WSL distribution

A run whose interpreter is a WSL interpreter SHALL start the bundled robotcode inside the interpreter's distribution through PyCharm's support for WSL interpreters, without requiring robotcode to be installed in the distribution. Every path that the run passes to robotcode, such as the files and folders of a "Files and folders" target, SHALL be passed as the path of the same file inside the distribution, for a project inside the distribution and for a project on a Windows drive. The connection between the debugger of the run and the IDE SHALL be forwarded by PyCharm, SHALL NOT need a firewall rule on Windows and SHALL work in every networking mode of WSL; inside the distribution, the debugger SHALL listen on the loopback address only.

#### Scenario: Gutter run of one test

- **WHEN** a project inside the distribution "Ubuntu" uses a WSL interpreter and the user runs "First Test Passes" from the gutter
- **THEN** the robot process runs inside "Ubuntu", only that test runs, and the Run tool window shows its result

#### Scenario: Files and folders target

- **WHEN** the target is "Files and folders" with `tests/other.robot` and the user runs the configuration with a WSL interpreter
- **THEN** robotcode receives the path of `tests/other.robot` inside the distribution, and only its tests run

#### Scenario: Project on a Windows drive

- **WHEN** a project in `C:\work\robot-project` uses a WSL interpreter and the user runs a suite from the gutter
- **THEN** the robot process runs inside the distribution with the project folder below the distribution's mount folder as working directory, and the suite's tests run

#### Scenario: Environment variable

- **WHEN** a configuration with a WSL interpreter sets the environment variable `FOO=bar` and runs a test that executes `Log    %{FOO}`
- **THEN** the log of the run contains `bar`

#### Scenario: Mirrored networking

- **WHEN** WSL runs in mirrored networking mode and the user debugs a test with a WSL interpreter
- **THEN** the debugger connects and the session starts as in WSL's default networking mode

## MODIFIED Requirements

### Requirement: Runs use the configuration's interpreter and environment

A run SHALL start the bundled `robotcode` with the configuration's Python interpreter, interpreter options, working directory and environment, prepared the way PyCharm prepares its own Python runs, including the activation of a virtualenv or conda interpreter. Without changes in the editor, a run SHALL use the Python interpreter that RobotCode uses for the language server, the project folder as working directory and no additional `PYTHONPATH` entries, as runs did before. A run whose interpreter is a WSL interpreter SHALL run inside the interpreter's distribution. A run whose interpreter is another remote one, such as Docker or SSH, SHALL NOT start a process and SHALL report that Robot Framework runs with remote interpreters are not supported yet. A configuration without a valid Python interpreter SHALL show an error before the run.

#### Scenario: Defaults

- **WHEN** the user runs a test from the gutter in a project with one module and its Python interpreter
- **THEN** the run uses that interpreter, starts in the project folder, and `PYTHONPATH` gets no entry from the project's roots

#### Scenario: WSL interpreter

- **WHEN** a configuration's interpreter is a WSL interpreter and the user runs it
- **THEN** the run starts inside the interpreter's distribution, and the Run tool window shows the results

#### Scenario: Remote interpreter

- **WHEN** a configuration's interpreter is a Docker or SSH interpreter and the user runs it
- **THEN** no process starts, and the user sees that Robot Framework runs with remote interpreters are not supported yet

#### Scenario: No interpreter

- **WHEN** a configuration has no valid Python interpreter
- **THEN** the run widget and the editor show an error for the configuration before it is run

#### Scenario: Content roots on the Python path

- **WHEN** the user enables adding content roots to `PYTHONPATH` and runs a suite that imports a Python library from a content root that is not on the Python path otherwise
- **THEN** the library is imported and the suite runs

### Requirement: Problems are reported before a run

While a Robot Framework run configuration is edited and when it is started, the plugin SHALL report these problems in addition to PyCharm's own check of the interpreter, which it SHALL NOT repeat:

- an error when RobotCode's environment check found the configuration's interpreter not usable, with the message of the result and a fix that opens the Python Interpreter settings;
- an error when the configuration's interpreter is a remote one other than a WSL interpreter, such as Docker or SSH, which Robot Framework runs do not support yet;
- a warning when the last check of the configuration's interpreter failed;
- an error that names each path of a "Files and folders" target that does not exist;
- a warning that names the items of a "Tests and suites" target that the current discovery does not contain, when discovery has a result.

An error SHALL keep the run from starting; a warning SHALL NOT. The validation SHALL use only results of the environment check that already exist, and SHALL NOT start a Python process while the IDE waits for it. When no result exists for the configuration's interpreter, it SHALL request a check in the background and report nothing about the interpreter.

#### Scenario: Interpreter without Robot Framework

- **WHEN** a configuration's interpreter was checked and has no Robot Framework, and the user starts the configuration
- **THEN** no robot process starts, the IDE shows the configuration with the error that Robot Framework is not installed, and its fix opens the Python Interpreter settings

#### Scenario: Remote interpreter

- **WHEN** a configuration's interpreter is a Docker or SSH interpreter
- **THEN** the editor shows the error that Robot Framework runs with remote interpreters are not supported yet, before the configuration is run

#### Scenario: Usable WSL interpreter

- **WHEN** a configuration's interpreter is a WSL interpreter that the environment check found usable
- **THEN** the editor shows no error about the interpreter, and the configuration can be started

#### Scenario: Path that does not exist

- **WHEN** the target is "Files and folders" with `tests/gone.robot`, which does not exist, and the user starts the configuration
- **THEN** no robot process starts, and the error names `tests/gone.robot`

#### Scenario: Renamed test

- **WHEN** the target is "Tests and suites" with an item whose test has been renamed, and discovery has a result
- **THEN** the editor shows a warning that names the item, and the configuration can still be started

#### Scenario: No interpreter

- **WHEN** a configuration has no Python interpreter
- **THEN** the editor shows PyCharm's own error about the missing interpreter, and no second error from RobotCode about it

#### Scenario: Interpreter not checked yet

- **WHEN** a configuration uses an interpreter that RobotCode has not checked yet, and the user opens the configuration in the editor
- **THEN** the editor opens without delay and reports nothing about the interpreter, and a check of it starts in the background
