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

### Requirement: The environment check runs in the background

The plugin SHALL check the interpreter in a background process that takes at most 30 seconds. Opening and editing files, the editor banner, the status bar, applying settings and starting the language server SHALL NOT wait for the check. While no result exists, the language server and test discovery SHALL NOT start; they SHALL start as soon as the check finds the interpreter usable.

#### Scenario: Slow interpreter

- **WHEN** the project's interpreter needs 35 seconds to answer and a Robot file is opened
- **THEN** the IDE stays responsive meanwhile, and after 30 seconds the editor shows that the check of the interpreter timed out

#### Scenario: Usable interpreter

- **WHEN** a project with Robot Framework files is opened and the check finds the interpreter usable
- **THEN** the language server and test discovery start without further action

### Requirement: A separate result for each problem

The check SHALL tell these results apart, and both the banner on Robot files and the error of a run SHALL name the one that applies together with the requirement "Python 3.10 or newer with Robot Framework 5.0 or newer":

- no Python interpreter is configured;
- the interpreter's path does not exist;
- the Python is older than 3.10, with the detected version;
- Robot Framework is not installed;
- Robot Framework is older than 5.0, with the detected version;
- the check failed or timed out.

#### Scenario: Old Robot Framework

- **WHEN** the project's interpreter has Robot Framework 4.1 installed and a Robot file is opened
- **THEN** no language server starts, and the banner says that Robot Framework 4.1 is older than 5.0 and names the requirement

#### Scenario: Robot Framework missing

- **WHEN** the project's interpreter is Python 3.12 without Robot Framework and a Robot file is opened
- **THEN** the banner says that Robot Framework is not installed in the interpreter and names the requirement

#### Scenario: Old Python

- **WHEN** the project's interpreter is Python 3.9 and a Robot file is opened
- **THEN** the banner says that Python 3.9 is older than 3.10 and names the requirement

### Requirement: Remote interpreters are a result of their own

The check SHALL also tell apart, as a result of its own, that the interpreter is a remote one, such as WSL, Docker or SSH, which RobotCode does not support yet; both the banner on Robot files and the error of a run SHALL name it together with the requirement "Python 3.10 or newer with Robot Framework 5.0 or newer". PyCharm without a Pro subscription does not count remote interpreters as Python interpreters, so there the result SHALL be that no interpreter is configured.

#### Scenario: Run with an SSH interpreter

- **WHEN** the project's interpreter is an SSH interpreter and the user starts a run
- **THEN** the error of the run says that RobotCode does not support remote interpreters yet and names the requirement

### Requirement: Remote interpreters are recognized without running them

The plugin SHALL recognize a remote interpreter without running a local process, also when a file with the interpreter's path exists on the local machine.

#### Scenario: Remote interpreter

- **WHEN** the project's interpreter is a remote interpreter whose path, such as `/usr/bin/python3`, also exists on the local machine
- **THEN** the banner says that RobotCode does not support remote interpreters yet, and no process runs with that path

### Requirement: A failed check is not a result

When the check process cannot be started, exits with an error, prints something unexpected or times out, the plugin SHALL NOT treat this as a result about the interpreter. It SHALL show that the check failed, SHALL write the command line, the exit code and the output of the check to idea.log as a warning, and SHALL check again on the next trigger: a restart of the language server, a change of the interpreter or of its SDK, or the start of a run.

#### Scenario: Timeout and retry

- **WHEN** the first check timed out, and the user chooses Restart RobotCode Language Server after the interpreter answers normally again
- **THEN** the plugin checks again and the language server starts

#### Scenario: Log entry

- **WHEN** a check times out
- **THEN** idea.log contains a warning with the command line of the check, and no "IDE error occurred" notification appears

### Requirement: Only a trigger starts a new check

Only a trigger SHALL start a new check of the interpreter, so that a failing check does not run again and again on its own.

#### Scenario: No trigger after a failed check

- **WHEN** a check failed and neither the language server restarts, nor the interpreter or its SDK changes, nor a run starts
- **THEN** no new check runs

### Requirement: Check again only when the interpreter changes

The plugin SHALL check the interpreter again, and restart the language server and test discovery, only when the interpreter RobotCode uses changes: another SDK is chosen, the path of the SDK changes, or the project SDK changes for modules that inherit it. While the interpreter is usable, a refresh of the SDK's paths, a change of excluded folders or a change of an SDK that RobotCode does not use SHALL NOT start a check or a restart.

#### Scenario: Switching the interpreter

- **WHEN** the user switches the project to another Python SDK with the interpreter widget in the status bar
- **THEN** the plugin checks the new interpreter once and restarts the language server once

#### Scenario: Project SDK inherited by a module

- **WHEN** in IntelliJ IDEA with the Python plugin the module inherits the project SDK and the user changes the project SDK
- **THEN** the plugin checks the new interpreter and restarts the language server with it

#### Scenario: Unrelated changes

- **WHEN** the paths of the usable SDK are refreshed, or a folder is excluded from the project
- **THEN** no check runs and the language server is not restarted

#### Scenario: Interpreter change after a failed start

- **WHEN** a start of the language server failed and the user switches the project to another usable interpreter
- **THEN** the plugin checks the new interpreter and starts the language server

### Requirement: An unusable interpreter is checked again when its SDK changes

While the interpreter is not usable, a change of its SDK, such as the refresh of its paths after packages were installed, SHALL start a new check.

#### Scenario: Packages installed into an unusable interpreter

- **WHEN** the banner says that Robot Framework is not installed, Robot Framework is then installed into the interpreter, and the paths of its SDK are refreshed
- **THEN** the plugin checks again, the banner disappears and the language server starts

### Requirement: The banner follows the result

The banner on Robot files SHALL appear, change or disappear as soon as the result changes, without reopening the file.

#### Scenario: Result arrives after the file was opened

- **WHEN** a Robot file is opened before the check has finished, and the check then finds Robot Framework missing
- **THEN** the banner appears on the open file without reopening it

### Requirement: Runs report an unusable interpreter

A run SHALL NOT start a robot process when the interpreter it uses is not usable. It SHALL fail with the IDE's run error, which names the result, and SHALL NOT log an IDE error. When a run starts before a result exists, or after the last check failed, it SHALL wait for a new check with a progress indication that can be cancelled, and then start or fail.

#### Scenario: No interpreter

- **WHEN** a saved Robot Framework run configuration is started with Run and with Debug while the project has no Python SDK
- **THEN** both show the IDE's "Error running" message saying that no Python interpreter is configured, no debug session starts, and idea.log gets no SEVERE entry

#### Scenario: Run right after opening a project

- **WHEN** a run starts before the first check of the project's interpreter has finished
- **THEN** a progress indication shows that the interpreter is being checked, and the run starts once the check finds the interpreter usable
