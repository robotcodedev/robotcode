# Spec Delta

## Purpose

Defines where RobotCode's VS Code extension runs tests and debug sessions: the console values of a run, RobotCode's own run terminal, how it is reused and closed, and the environment of a run in it.

## ADDED Requirements

### Requirement: Console values of a run

The setting `robotcode.debug.defaultConsole` and the attribute `console` of RobotCode's launch configurations SHALL offer `robotcodeTerminal`, `integratedTerminal`, `internalConsole` and `externalTerminal`, and `robotcodeTerminal` SHALL be the default of both. A launch configuration's `console` SHALL take precedence over the setting. `integratedTerminal`, `internalConsole` and `externalTerminal` SHALL behave as before this change.

#### Scenario: No console set

- **WHEN** neither the setting nor the launch configuration sets a console and the user runs a test from the Test Explorer
- **THEN** the test runs in RobotCode's run terminal

#### Scenario: Integrated terminal chosen

- **WHEN** `robotcode.debug.defaultConsole` is `integratedTerminal` and the user runs a test
- **THEN** the run's command is typed into a shell of VS Code's integrated terminal, as before this change

#### Scenario: Launch configuration overrides the setting

- **WHEN** the setting is `integratedTerminal` and a launch configuration with `"console": "robotcodeTerminal"` is started
- **THEN** that run runs in RobotCode's run terminal

### Requirement: A run is the process of the run terminal

With `robotcodeTerminal`, a run or debug session SHALL run as the process of a terminal that RobotCode creates, without a shell, with the interpreter that RobotCode uses for the workspace folder. No command typed by VS Code or by a Python extension, such as an activation command, SHALL reach the run, and every run SHALL get the same environment, whether its terminal is new or reused.

#### Scenario: No activation text with the Python Environments extension

- **WHEN** the Python Environments extension activates environments in new terminals and the user runs a test twice
- **THEN** no activation command appears in the terminal or reaches the run, and both runs see the same environment variables

#### Scenario: No activation text with the Python extension alone

- **WHEN** `python.useEnvironmentsExtension` is `false` and the user runs a test
- **THEN** no activation command appears in the terminal or reaches the run

### Requirement: The run terminal is the run's input and output

The run SHALL have the terminal as its standard input and output, as in a shell: Robot Framework's console colors and progress line SHALL work, and Ctrl+C in the terminal SHALL reach the run and not close the terminal.

#### Scenario: Console of the run is a terminal

- **WHEN** a test in the run checks whether its standard output is a terminal
- **THEN** it is

#### Scenario: Ctrl+C during a run

- **WHEN** the user presses Ctrl+C in the run terminal while a test runs
- **THEN** Robot Framework stops the run as on Ctrl+C in a shell, and the terminal stays open with the run's output

### Requirement: Name and icon of the run terminal

A run terminal SHALL carry the name of the run's debug session, such as "RobotCode: Run Tests" with the workspace folder's name, and RobotCode's robot icon.

#### Scenario: Run from the Test Explorer

- **WHEN** the user runs a test of the folder `robotcode-demo` from the Test Explorer
- **THEN** the run terminal is named after the run's session and shows the robot icon

### Requirement: The run terminal waits after a run

When a run ends, its terminal SHALL keep the run's output and show the line ` * Terminal will be reused by RobotCode runs, press any key to close it.` A key pressed in the terminal after that line SHALL close the terminal.

#### Scenario: Passed run

- **WHEN** a run ends with all tests passed
- **THEN** the terminal stays open with the run's output and the line about its reuse

#### Scenario: Key after the run

- **WHEN** the line about the reuse is shown and the user presses a key in the terminal
- **THEN** the terminal closes

### Requirement: The run terminal is reused

A run SHALL run in a run terminal that has the same name, belongs to the same workspace folder and has no run in progress, below the output of the earlier runs. When no such terminal exists, the run SHALL get a new run terminal, also when another run is still in progress in a terminal of that name.

#### Scenario: Second run

- **WHEN** a run ended in a run terminal and the user starts a run with the same name in the same folder
- **THEN** the second run runs in that terminal, below the output of the first run

#### Scenario: Run while another is in progress

- **WHEN** a run is in progress in a run terminal and a run with the same name starts in the same folder
- **THEN** the new run gets a run terminal of its own

#### Scenario: Run terminal closed by the user

- **WHEN** the user closed the run terminal and starts the run again
- **THEN** the run gets a new run terminal

### Requirement: Run terminals are not restored

VS Code SHALL NOT restore a run terminal when the window is reloaded or VS Code starts again.

#### Scenario: Window reloaded

- **WHEN** a run terminal is open and the user reloads the window
- **THEN** no run terminal appears after the reload

### Requirement: The session ends with the run

**Stop** in the debug toolbar SHALL end a run in a run terminal as with the other console values. When the run's process ends, its debug session SHALL end, also when the process ends before the debugger connected to it, and the process's output SHALL stay in the terminal.

#### Scenario: Run that cannot start

- **WHEN** the run's process ends at once with an error, before the debugger connected
- **THEN** the debug session ends without waiting for the launcher's timeout, and the terminal shows the error and the line about its reuse

#### Scenario: Stop during a run

- **WHEN** the user presses **Stop** in the debug toolbar while a test runs in a run terminal
- **THEN** the run ends as with `integratedTerminal`, and the terminal shows the run's output and the line about its reuse

### Requirement: Debug clients other than VS Code

When a debug client other than VS Code asks RobotCode's debug launcher for `robotcodeTerminal`, the launcher SHALL start the run as for `integratedTerminal`.

#### Scenario: Other client

- **WHEN** a launch request with `"console": "robotcodeTerminal"` comes from a client whose `clientID` is not `vscode`
- **THEN** the launcher asks that client with `runInTerminal`, as for `integratedTerminal`
