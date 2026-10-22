# vscode-run-terminal Specification

## Purpose

Defines where RobotCode's VS Code extension runs tests and debug sessions: the console values of a run, RobotCode's own run terminal, how it is reused and closed, and the environment of a run in it.

## Requirements

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

On every platform that VS Code runs on, the run SHALL have the terminal as its standard input and output, as in a shell: Robot Framework's console colors and progress line SHALL work, and every Ctrl+C in the terminal SHALL reach the run and not close the terminal.

#### Scenario: Console of the run is a terminal

- **WHEN** a test in the run checks whether its standard output is a terminal
- **THEN** it is

#### Scenario: Ctrl+C during a run

- **WHEN** the user presses Ctrl+C in the run terminal while a test runs
- **THEN** Robot Framework stops the run as on Ctrl+C in a shell, and the terminal stays open with the run's output

#### Scenario: Run on Windows

- **WHEN** a test runs in a run terminal on Windows
- **THEN** the terminal shows the line before the run and the run's output, and the run's standard input and output are a terminal

#### Scenario: Ctrl+C a second time

- **WHEN** Robot Framework is stopping a run after a first Ctrl+C, for example in a teardown, and the user presses Ctrl+C again
- **THEN** Robot Framework ends the run at once, as in a shell, and the terminal stays open with the run's output

### Requirement: The run terminal shows the command line

Before each run, the run terminal SHALL show the run's command line, the program and its arguments, in one line `Executing: <command line>` that is marked as VS Code marks its own terminal messages, with ` * ` in inverse video before it. The interpreter and RobotCode's script SHALL appear as `robotcode`, as one types it in a terminal. An argument that contains a space, a quote or another character that a shell would read SHALL be quoted. The line SHALL NOT list environment variables.

#### Scenario: Run with a profile

- **WHEN** the configuration profile `ci` is selected and the user runs a test
- **THEN** the run terminal shows the marked line `Executing: robotcode -p ci` and the further arguments of the run before the run's output, without the interpreter's path and the path of RobotCode's script

#### Scenario: Reused terminal

- **WHEN** a second run starts in a run terminal
- **THEN** the terminal shows the command line of the second run before its output, below the output of the first run

#### Scenario: Argument with a space

- **WHEN** an argument of the run, such as the long name of a suite, contains a space
- **THEN** the line shows that argument quoted

### Requirement: Each run is a command of the terminal

Each run SHALL be a command for VS Code's shell integration: its marked command line SHALL carry VS Code's command decoration, colored by the run's exit code, whose menu offers copying the full command line and the run's output, and VS Code's sticky scroll SHALL keep it at the top while the run's output scrolls. **Rerun Command**, **Run Recent Command** and text pasted into the terminal SHALL neither start a run nor close the terminal.

#### Scenario: Decoration of a passed and a failed run

- **WHEN** a run passes and a second run in the same terminal fails
- **THEN** the command line of the first run carries the decoration of a successful command and that of the second the decoration of a failed one

#### Scenario: Copy the command line of a run

- **WHEN** the user chooses **Copy Command** in the menu of a run's decoration
- **THEN** the clipboard holds the full command line of the run, with the interpreter and the path of RobotCode's script

#### Scenario: Copy the output of a run

- **WHEN** the user chooses **Copy Output** in the menu of a run's decoration
- **THEN** the clipboard holds the output of that run, without the command line and without the line about the reuse

#### Scenario: Sticky scroll

- **WHEN** the user scrolls through the output of a run so far that its command line leaves the view
- **THEN** VS Code shows the run's command line at the top of the terminal, as for the commands of a shell

#### Scenario: Rerun Command after the run

- **WHEN** the user chooses **Rerun Command** in the menu of a run's decoration and confirms VS Code's question
- **THEN** no run starts and the terminal stays open

### Requirement: Name and icon of the run terminal

A run terminal SHALL carry the name of the run's debug session, such as "RobotCode: Run Tests" with the workspace folder's name, and RobotCode's robot icon.

#### Scenario: Run from the Test Explorer

- **WHEN** the user runs a test of the folder `robotcode-demo` from the Test Explorer
- **THEN** the run terminal is named after the run's session and shows the robot icon

### Requirement: The run terminal waits after a run

When a run ends, its terminal SHALL keep the run's output and show the line `Terminal will be reused by RobotCode runs, press any key to close it.`, marked as the command line is. When RobotCode's extension no longer runs, as after a restart of the extension host, the line SHALL be `Press any key to close the terminal.` instead. A key pressed in the terminal after that line SHALL close the terminal.

#### Scenario: Passed run

- **WHEN** a run ends with all tests passed
- **THEN** the terminal stays open with the run's output and the line about its reuse

#### Scenario: Extension host restarted during a run

- **WHEN** VS Code's extension host restarts while a run is in progress in a run terminal
- **THEN** the run goes on, and after it the terminal keeps the output, shows the line about closing it and closes on a key

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

### Requirement: Environment names of a run on Windows

On Windows, with `robotcodeTerminal` and with `internalConsole`, a variable that a run's environment sets SHALL replace an inherited variable whose name differs only in case, with every supported Python version, so that the run and the programs it starts see the same, new value.

#### Scenario: Lower-case name in the run terminal

- **WHEN** Windows has `Path`, `robotcode.robot.env` sets `path`, and the user runs a test with `robotcodeTerminal`
- **THEN** the run and a program that the run starts see the value of `path`

#### Scenario: Other spelling with the internal console and Python 3.10

- **WHEN** the run's interpreter is Python 3.10, the launch configuration sets `Path` in `env`, and the run uses `internalConsole`
- **THEN** the run and a program that the run starts see the value from the launch configuration

#### Scenario: Other platforms

- **WHEN** a run's environment on Linux or macOS sets `path` while `PATH` exists
- **THEN** the run gets both variables, as before
