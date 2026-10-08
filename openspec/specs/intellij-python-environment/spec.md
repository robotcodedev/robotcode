# intellij-python-environment Specification

## Purpose

Defines which Python interpreter the IntelliJ plugin uses for RobotCode, which interpreters it accepts, how and when it checks them, and what it tells the user about an interpreter it cannot use.

## Requirements

### Requirement: Minimum Python and Robot Framework versions

The plugin SHALL start the language server, run test discovery and start runs only with a Python interpreter of version 3.10 or newer that has Robot Framework 5.0 or newer installed. Every message about an interpreter that does not meet this, in the editor and in the error of a run, SHALL name the requirement "Python 3.10 or newer with Robot Framework 5.0 or newer".

#### Scenario: Python 3.9

- **WHEN** the project's interpreter is Python 3.9 with Robot Framework installed, and a Robot file is opened
- **THEN** no language server starts, and the editor shows a message that the interpreter is older than Python 3.10 and that RobotCode needs Python 3.10 or newer with Robot Framework 5.0 or newer

#### Scenario: Python 3.10 with Robot Framework

- **WHEN** the project's interpreter is Python 3.10 with Robot Framework 7 installed
- **THEN** the language server starts

#### Scenario: Robot Framework missing

- **WHEN** the project's interpreter is Python 3.12 without Robot Framework, and a Robot file is opened
- **THEN** no language server starts, and the editor shows a message that names Python 3.10 or newer with Robot Framework 5.0 or newer as the requirement

#### Scenario: Run with an unsupported interpreter

- **WHEN** a Robot Framework run configuration is started while the project's interpreter is Python 3.9
- **THEN** no robot process starts, and the error of the run names Python 3.10 or newer with Robot Framework 5.0 or newer as the requirement
