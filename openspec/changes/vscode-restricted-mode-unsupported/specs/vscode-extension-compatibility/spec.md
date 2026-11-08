# Spec Delta: vscode-extension-compatibility

## ADDED Requirements

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
