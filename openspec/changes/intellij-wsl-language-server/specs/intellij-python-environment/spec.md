# Spec Delta

## Purpose

Defines which Python interpreter the IntelliJ plugin uses for RobotCode, which interpreters it accepts, how and when it checks them, and what it tells the user about an interpreter it cannot use.

## ADDED Requirements

### Requirement: WSL interpreters are checked inside their distribution

When the interpreter RobotCode uses is a WSL interpreter of PyCharm on Windows, the plugin SHALL check it by running it inside its WSL distribution, never as a process on the Windows side, with the same minimum versions, time limit and handling of a failed check as for a local interpreter. Before it runs the interpreter, the plugin SHALL verify that the interpreter's distribution is installed and that the project folder can be reached from it. The check SHALL also verify that RobotCode's bundled files can be reached from inside the distribution.

#### Scenario: Usable WSL interpreter

- **WHEN** the project's interpreter is a WSL interpreter with Python 3.12 and Robot Framework 7 in the distribution "Ubuntu", and a Robot file of the project is opened
- **THEN** the check runs inside "Ubuntu", finds the interpreter usable, and the language server starts

#### Scenario: Old Python inside WSL

- **WHEN** the project's WSL interpreter is Python 3.9
- **THEN** the banner says that Python 3.9 is older than 3.10 and names the requirement, as for a local interpreter

#### Scenario: Distribution no longer installed

- **WHEN** the project's WSL interpreter belongs to a distribution that has been uninstalled
- **THEN** the banner says that the interpreter's WSL distribution is not installed, and the interpreter is not started

#### Scenario: Windows drives not mounted

- **WHEN** the distribution does not mount the Windows drives, so that the plugin's folder is not visible inside it
- **THEN** the banner says that RobotCode cannot reach its bundled files from the distribution and that WSL must mount the Windows drives

#### Scenario: Project in another distribution

- **WHEN** the project lies in the distribution "Debian" and its interpreter in the distribution "Ubuntu"
- **THEN** the banner says that the project folder cannot be reached from the interpreter's distribution, and the interpreter is not started

### Requirement: Every robotcode process of a WSL project runs inside the distribution

For a project whose interpreter is a WSL interpreter, every robotcode process the plugin starts for the project, other than Run and Debug, SHALL run inside the interpreter's distribution, as the distribution's default user, with the bundled robotcode from the plugin's folder and the project folder as working directory. Environment variables of the IDE's Windows environment SHALL NOT be passed on to these processes, and output of the distribution's shell startup files SHALL NOT reach them.

#### Scenario: No robotcode process on Windows

- **WHEN** a project with a WSL interpreter is opened and the language server and discovery have started
- **THEN** the language server and discovery processes run inside the distribution, and no robotcode process runs on the Windows side

#### Scenario: Configuration in the distribution's home folder

- **WHEN** the user's `~/.config/robotcode/robot.toml` inside the distribution sets `default-profiles` to a profile that sets a variable, and a suite of the project uses that variable
- **THEN** the language server reports no error for the variable

#### Scenario: Shell startup file that prints

- **WHEN** the user's shell startup files inside the distribution print a line
- **THEN** the language server and discovery still start and work

### Requirement: Runs with a WSL interpreter are not supported yet

When a Robot Framework run configuration is started with Run or Debug and the interpreter it uses is a WSL interpreter, the plugin SHALL NOT start a process and SHALL show the IDE's run error, which says that Robot Framework runs with WSL and other remote interpreters are not supported yet. It SHALL NOT log an IDE error.

#### Scenario: Gutter run in a WSL project

- **WHEN** the user runs a test from the gutter, with Run and with Debug, in a project whose interpreter is a WSL interpreter
- **THEN** both show "Error running" with the message that such runs are not supported yet, no robot process starts on either side, and idea.log gets no SEVERE entry

## MODIFIED Requirements

### Requirement: A separate result for each problem

The check SHALL tell these results apart, and both the banner on Robot files and the error of a run SHALL name the one that applies together with the requirement "Python 3.10 or newer with Robot Framework 5.0 or newer":

- no Python interpreter is configured;
- the interpreter's path does not exist;
- the Python is older than 3.10, with the detected version;
- Robot Framework is not installed;
- Robot Framework is older than 5.0, with the detected version;
- the interpreter is a remote one other than a WSL interpreter, such as Docker or SSH, which RobotCode does not support yet;
- the WSL distribution of a WSL interpreter is not installed;
- RobotCode's bundled files cannot be reached from inside the WSL distribution;
- the project folder cannot be reached from the WSL distribution of the interpreter;
- the check failed or timed out.

The plugin SHALL recognize a remote interpreter, including a WSL interpreter, without running a local process, also when a file with the interpreter's path exists on the local machine.

#### Scenario: Old Robot Framework

- **WHEN** the project's interpreter has Robot Framework 4.1 installed and a Robot file is opened
- **THEN** no language server starts, and the banner says that Robot Framework 4.1 is older than 5.0 and names the requirement

#### Scenario: Robot Framework missing

- **WHEN** the project's interpreter is Python 3.12 without Robot Framework and a Robot file is opened
- **THEN** the banner says that Robot Framework is not installed in the interpreter and names the requirement

#### Scenario: Old Python

- **WHEN** the project's interpreter is Python 3.9 and a Robot file is opened
- **THEN** the banner says that Python 3.9 is older than 3.10 and names the requirement

#### Scenario: Remote interpreter

- **WHEN** the project's interpreter is a Docker or SSH interpreter whose path, such as `/usr/bin/python3`, also exists on the local machine
- **THEN** the banner says that RobotCode does not support remote interpreters yet, and no process runs with that path

#### Scenario: WSL interpreter whose path exists on Windows

- **WHEN** the project's interpreter is a WSL interpreter whose path, such as `/usr/bin/python3`, also exists on the Windows side
- **THEN** the interpreter is checked inside its distribution, and no process runs with that path on the Windows side
