# vscode-terminal-repl Specification

## Purpose

Defines how RobotCode's VS Code extension starts the RobotCode REPL in a terminal of VS Code: in which workspace folder and Python environment, with which settings, how the terminal behaves, and what the user sees when the REPL cannot start.

## Requirements

### Requirement: The REPL runs in the folder's environment

**RobotCode: Start Terminal REPL** SHALL start the REPL of RobotCode's bundled tool in a new terminal whose process is RobotCode's terminal script, in the workspace folder, with the interpreter that RobotCode uses for that folder, the same as for its language server, for both the script and the REPL. It SHALL NOT type a command into a shell, and no activation command of the Python extensions SHALL reach the REPL.

#### Scenario: Python Environments extension active

- **WHEN** the folder's `.venv` with Robot Framework is selected and the Python Environments extension activates new terminals by sending a command
- **THEN** the REPL starts with the interpreter of `.venv`, its prompt waits for input, and no `source …/activate` or other activation text appears in the REPL

#### Scenario: Python extension without the Python Environments extension

- **WHEN** `python.useEnvironmentsExtension` is `false` and the Python extension's API reports the folder's `.venv` with Robot Framework
- **THEN** the REPL starts with the interpreter of `.venv` and no activation text appears in the REPL

#### Scenario: Another robotcode on the PATH

- **WHEN** a `robotcode` without the `repl` command comes first on the PATH of the user's shell
- **THEN** the REPL starts nevertheless, from RobotCode's bundled tool

#### Scenario: Ctrl+C at the prompt

- **WHEN** the user presses Ctrl+C at the REPL's prompt
- **THEN** the REPL handles it as without the script, and the terminal stays open

### Requirement: The REPL gets the settings of runs

The REPL SHALL get the folder's settings that test runs get: `robotcode.extraArgs`, the selected configuration profiles, `robotcode.robot.pythonPath` as Python path, `robotcode.robot.variables` as variables, `robotcode.robot.variableFiles` as variable files, and `robotcode.robot.env` as environment variables of the process.

#### Scenario: Variables

- **WHEN** `robotcode.robot.variables` of the folder sets `HOST` to `staging`, and the user enters `Log    ${HOST}` in the REPL
- **THEN** the REPL logs `staging`

#### Scenario: Profiles

- **WHEN** the configuration profile `ci` is selected for the folder
- **THEN** the REPL starts with the profile `ci`

#### Scenario: Environment variables

- **WHEN** `robotcode.robot.env` sets `SHOP_URL` to `http://localhost:8080`, and the user enters `Log    %{SHOP_URL}` in the REPL
- **THEN** the REPL logs `http://localhost:8080`

### Requirement: The folder is chosen as before

The command SHALL start the REPL for the folder it is given, as from the RobotCode menu; otherwise for the folder of the active editor; otherwise for the only workspace folder; otherwise for a folder the user picks, and for none when the pick is cancelled. In a workspace with several folders the terminal's name SHALL contain the folder's name.

#### Scenario: Several folders, no active editor

- **WHEN** the workspace has the folders `shop` and `admin`, no editor is active, and the user runs the command and picks `admin`
- **THEN** a terminal named after `admin` starts the REPL of `admin`

#### Scenario: Pick cancelled

- **WHEN** the user cancels the folder pick
- **THEN** no terminal opens and no message appears

### Requirement: An unusable environment shows an error

When the folder's Python environment cannot run the REPL, because no interpreter is selected, the interpreter is missing, Python is older than 3.10, or Robot Framework is missing or older than 5.0, the command SHALL show an error message that names the folder and the problem, and SHALL NOT open a terminal. For a folder for which RobotCode is switched off, the error message SHALL say so.

#### Scenario: Robot Framework missing

- **WHEN** the selected Python environment of the folder `shop` has no Robot Framework and the user runs the command
- **THEN** an error message says that the REPL for `shop` cannot start because the selected Python environment has no Robot Framework, and no terminal opens

#### Scenario: Problem solved since the last check

- **WHEN** RobotCode found no Robot Framework in the folder's environment, the user installs it there, and runs the command before RobotCode looked again
- **THEN** the REPL starts, without an error message

#### Scenario: Folder switched off

- **WHEN** `robotcode.disableExtension` is `true` for the folder and the user runs the command
- **THEN** an error message says that RobotCode is switched off for the folder by that setting, and no terminal opens

### Requirement: The REPL terminal ends with the REPL

The REPL terminal SHALL close when the REPL ends with the exit code 0, for example with `.exit`, without a further message. When the REPL ends with another exit code, as after an error, the terminal SHALL keep the REPL's output, show ` * Press any key to close the terminal.` below it, and close at the next key, without a message about the exit code. The terminal SHALL NOT be restored when VS Code starts again.

#### Scenario: Exit

- **WHEN** the user enters `.exit` in the REPL
- **THEN** the terminal closes and no notification appears

#### Scenario: Restart of VS Code

- **WHEN** a REPL terminal is open and VS Code is closed and started again
- **THEN** no REPL terminal is restored

#### Scenario: Mistyped profile in the folder settings

- **WHEN** the folder settings set `robotcode.profiles` to `["typo"]`, the folder's `robot.toml` defines no profile `typo`, and the user runs the command
- **THEN** the REPL's terminal opens and shows `[ ERROR ] No profile matches 'typo'.` and ` * Press any key to close the terminal.`, no notification about the selection appears, and the terminal closes at the next key without a notification

#### Scenario: Selection fixed

- **WHEN** the user removes `typo` from `robotcode.profiles` and runs the command again
- **THEN** the REPL starts, without `-p typo`
