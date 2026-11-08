# Spec: vscode-extension-compatibility

## Purpose

Defines which VS Code versions the RobotCode extension for VS Code supports, and which Node.js runtime it is built for, so that users know what they need and the extension runs in every version it can be installed in.

## Requirements

### Requirement: Supported VS Code versions

The VS Code extension SHALL run in VS Code 1.131.0 and every newer version, and SHALL declare 1.131.0 as its minimum, so that VS Code does not install it in an older version. The README and the Get Started page of the documentation SHALL name VS Code 1.131 as the minimum.

#### Scenario: Oldest supported version
- **WHEN** the extension is installed in VS Code 1.131.0 and a folder with Robot Framework files is opened
- **THEN** the extension activates, and its language features, test discovery and Keywords view work

#### Scenario: Older VS Code
- **WHEN** this version of the extension is installed in VS Code 1.130
- **THEN** VS Code does not install it, because it is not compatible

#### Scenario: Documented minimum
- **WHEN** a user reads the requirements in the README or on the Get Started page
- **THEN** both name VS Code 1.131 as the minimum

### Requirement: Node.js runtime of the extension

The extension SHALL run on Node.js 24, the Node.js of VS Code's extension host from VS Code 1.123 on, desktop and remote alike, and SHALL NOT need JavaScript syntax or Node.js APIs that Node.js 24.18, the version of VS Code 1.131.0, lacks.

#### Scenario: Extension host of the oldest supported version
- **WHEN** the extension activates in the extension host of VS Code 1.131.0, which runs Node.js 24.18
- **THEN** it activates without an error caused by syntax or an API that Node.js 24.18 does not support

#### Scenario: Remote window
- **WHEN** the extension runs in a WSL, SSH or dev container window of VS Code 1.131.0, whose remote extension host runs Node.js 24.18
- **THEN** it activates as in a local window

### Requirement: Python interpreters the extension accepts

The VS Code extension SHALL start the language server for a workspace folder only when the folder's Python interpreter is version 3.10 or newer, the version every RobotCode package requires, with Robot Framework 5.0 or newer. For an older Python, it SHALL show the environment message of `vscode-python-environment` that names Python 3.10 or newer as the requirement.

#### Scenario: Python 3.9

- **WHEN** the Python interpreter of a workspace folder with Robot Framework files is Python 3.9 and a Robot file is opened
- **THEN** the extension does not start the language server for the folder, and it shows the message that says that Python 3.10 or newer is required, with the links **Select Environment**, **Create Environment** and **Retry** and the button **Cancel**

#### Scenario: Python 3.10

- **WHEN** the Python interpreter of the workspace folder is Python 3.10 with Robot Framework 7 installed
- **THEN** the extension starts the language server for the folder

### Requirement: Untrusted workspaces

The VS Code extension SHALL declare that it does not support untrusted workspaces, so that VS Code keeps it disabled in Restricted Mode, whatever the extensions it depends on declare. While the workspace is untrusted, RobotCode SHALL run no code of the workspace: no language server, no test discovery and no `robotcode` process. Once the user trusts the workspace, the extension SHALL start without a reload of the window.

#### Scenario: Folder opened in Restricted Mode
- **WHEN** a folder with a `robot.toml` and Robot Framework files is opened in Restricted Mode
- **THEN** RobotCode is disabled, starts no language server, discovers no tests and starts no `robotcode` process, so neither the `expr` values of the `robot.toml` are evaluated nor the folder's Python libraries imported

#### Scenario: Python extension that runs in Restricted Mode
- **WHEN** the folder is opened in Restricted Mode with a Python extension that declares support for untrusted workspaces
- **THEN** RobotCode stays disabled all the same, and none of the folder's code runs

#### Scenario: Folder trusted
- **WHEN** the user trusts the folder opened in Restricted Mode
- **THEN** RobotCode activates without a reload of the window, starts the language server for the folder and discovers its tests
