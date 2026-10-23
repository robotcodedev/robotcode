# vscode-environment-info Specification

## Purpose

Lets users of RobotCode in VS Code copy the versions that a report about RobotCode, Robot Framework or Robocop needs, in a form they can paste into an issue, a forum post or a chat.

## Requirements

### Requirement: Copy the versions of a workspace folder

The command "RobotCode: Copy Environment Info" SHALL copy the versions of one workspace folder to the clipboard as a Markdown list with the lines VS Code Version, RobotCode Version, OS, Python Version, RobotFramework Version and Additional tools, named like the fields of RobotCode's bug report template. A short message SHALL confirm the copy.

#### Scenario: Folder with a working environment

- **WHEN** the folder's environment is a venv with Python 3.13.12, Robot Framework 7.5 and Robocop 6.2.0, VS Code 1.142.0 with RobotCode 2.8.0 runs on Linux, and the user runs the command
- **THEN** the clipboard holds a list like:

  ```
  - VS Code Version: 1.142.0
  - RobotCode Version: 2.8.0
  - OS: Linux x64 6.8.0
  - Python Version: 3.13.12 (venv)
  - RobotFramework Version: 7.5
  - Additional tools: robotframework-robocop==6.2.0
  ```

  and a message says that the environment info of the folder was copied

#### Scenario: Robocop not installed

- **WHEN** the folder's environment has no Robocop
- **THEN** the line reads `- Additional tools: none`

### Requirement: The folder of the versions

The command SHALL copy the versions of the folder it is given from the RobotCode menu, else of the folder of the active editor, else of the only folder of the workspace, and else of the folder the user picks. Without a workspace folder, the lines that depend on one SHALL read "unknown".

#### Scenario: Two folders, editor in the second

- **WHEN** the workspace has the folders `api` and `web`, the active editor shows a file of `web`, and the user runs the command from the Command Palette
- **THEN** the list holds the versions of `web`

#### Scenario: Two folders, no editor

- **WHEN** the workspace has two folders, no editor is open, and the user runs the command
- **THEN** RobotCode asks for the folder and copies its versions

### Requirement: Versions without a running language server

From the Command Palette, the command SHALL copy the list also when the folder's language server doesn't run. A version that only the language server knows SHALL read "unknown". Robot Framework SHALL read what the check of the environment found, and Python what the Python side reports, as the language status shows them.

#### Scenario: Robot Framework missing

- **WHEN** the folder's environment has no Robot Framework, so that its language server doesn't run, and the user runs the command
- **THEN** the list has `- RobotFramework Version: not installed` and `- Additional tools: unknown`, and the other lines as usual

#### Scenario: No interpreter

- **WHEN** no Python interpreter is selected for the folder, and the user runs the command
- **THEN** the list has `- Python Version: no interpreter selected`

### Requirement: No paths in the list

The list SHALL NOT contain paths: not the interpreter's, not the workspace's and not RobotCode's. The Python line SHALL name the version and, when the Python side reports it, the kind of the environment.

#### Scenario: Environment in the home directory

- **WHEN** the folder's interpreter is `/home/alice/shop/.venv/bin/python` with Python 3.12.4
- **THEN** the line reads `- Python Version: 3.12.4 (venv)`, and the list contains neither `alice` nor `/home`

### Requirement: Lines for particular setups

The list SHALL add the line Editor when the editor isn't VS Code, the line Remote when the window works on a remote, and the line RobotCode Language Server Version when the folder's language server runs another RobotCode version than the extension. Without such a setup, these lines SHALL NOT appear.

#### Scenario: Another editor

- **WHEN** the user runs the command in Cursor
- **THEN** the list has a line `- Editor: Cursor`

#### Scenario: Remote

- **WHEN** the window works on a folder in WSL
- **THEN** the list has a line `- Remote: wsl`, and the OS line names the system of WSL

#### Scenario: Language server from the environment

- **WHEN** the folder's language server runs RobotCode 2.7.0 from the environment while the extension is 2.8.0
- **THEN** the list has `- RobotCode Version: 2.8.0` and a line `- RobotCode Language Server Version: 2.7.0`

#### Scenario: Plain setup

- **WHEN** the user runs the command in VS Code on a local folder whose language server runs the extension's RobotCode
- **THEN** the list has only the six lines of the bug report template

### Requirement: Copy from the RobotCode menu

The RobotCode menu SHALL offer "Copy Environment Info" next to "Report Issue", and the entry SHALL copy the list of the menu's folder.

#### Scenario: From the language status

- **WHEN** the user clicks **Show Tool Menu** at the RobotCode item of the language status and then **Copy Environment Info**
- **THEN** the clipboard holds the list of the folder of the active editor
