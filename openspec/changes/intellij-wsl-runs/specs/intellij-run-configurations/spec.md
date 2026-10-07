# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: Runs inside the WSL distribution

A run whose interpreter is a WSL interpreter SHALL start the bundled robotcode inside the interpreter's distribution through PyCharm's support for WSL interpreters, without requiring robotcode to be installed in the distribution. Every path that the run passes to robotcode, such as the files and folders of a "Files and folders" target, SHALL be passed as the path of the same file inside the distribution, for a project inside the distribution and for a project on a Windows drive.

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

### Requirement: Debugger connection of a WSL run

The connection between the debugger of a run with a WSL interpreter and the IDE SHALL be forwarded by PyCharm, SHALL NOT need a firewall rule on Windows and SHALL work in every networking mode of WSL; inside the distribution, the debugger SHALL listen on the loopback address only.

#### Scenario: Mirrored networking

- **WHEN** WSL runs in mirrored networking mode and the user debugs a test with a WSL interpreter
- **THEN** the debugger connects and the session starts as in WSL's default networking mode

## MODIFIED Requirements

### Requirement: Runs with remote interpreters

A run whose interpreter is a WSL interpreter SHALL run inside the interpreter's distribution. A run whose interpreter is another remote one, such as Docker or SSH, SHALL NOT start a process and SHALL report that Robot Framework runs with remote interpreters are not supported yet.

#### Scenario: WSL interpreter

- **WHEN** a configuration's interpreter is a WSL interpreter and the user runs it
- **THEN** the run starts inside the interpreter's distribution, and the Run tool window shows the results

#### Scenario: Remote interpreter

- **WHEN** a configuration's interpreter is a Docker or SSH interpreter and the user runs it
- **THEN** no process starts, and the user sees that Robot Framework runs with remote interpreters are not supported yet

### Requirement: Remote interpreters are reported before a run

While a Robot Framework run configuration is edited and when it is started, the plugin SHALL report an error when the configuration's interpreter is a remote one other than a WSL interpreter, such as Docker or SSH, which Robot Framework runs do not support yet.

#### Scenario: Remote interpreter

- **WHEN** a configuration's interpreter is a Docker or SSH interpreter
- **THEN** the editor shows the error that Robot Framework runs with remote interpreters are not supported yet, before the configuration is run

#### Scenario: Usable WSL interpreter

- **WHEN** a configuration's interpreter is a WSL interpreter that the environment check found usable
- **THEN** the editor shows no error about the interpreter, and the configuration can be started
