## MODIFIED Requirements

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
- **THEN** the REPL's terminal opens and shows `Error: No profile matches 'typo'.` and ` * Press any key to close the terminal.`, no notification about the selection appears, and the terminal closes at the next key without a notification

#### Scenario: Selection fixed

- **WHEN** the user removes `typo` from `robotcode.profiles` and runs the command again
- **THEN** the REPL starts, without `-p typo`

## REMOVED Requirements

### Requirement: A selected profile that does not exist stops the start

**Reason**: The REPL's terminal now stays open after the REPL ends with an error, until a key (requirement "The REPL terminal ends with the REPL"), so the error of such a selection is readable there, as in the Documentation Viewer and in runs.

**Migration**: None. The notification with **Remove from Selection** and **Select Configuration Profiles** still appears when the folder's language server starts.
