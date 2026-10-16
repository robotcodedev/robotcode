# Spec Delta

## MODIFIED Requirements

### Requirement: Python interpreters the extension accepts

The VS Code extension SHALL start the language server for a workspace folder only when the folder's Python interpreter is version 3.10 or newer, the version every RobotCode package requires, with Robot Framework 5.0 or newer. For an older Python, it SHALL show the environment notification of `vscode-python-environment` that names Python 3.10 or newer as the requirement.

#### Scenario: Python 3.9

- **WHEN** the Python interpreter of a workspace folder with Robot Framework files is Python 3.9 and a Robot file is opened
- **THEN** the extension does not start the language server for the folder, and it shows the notification that says that Python 3.10 or newer is required, with **Select Environment** and **Create Environment**

#### Scenario: Python 3.10

- **WHEN** the Python interpreter of the workspace folder is Python 3.10 with Robot Framework 7 installed
- **THEN** the extension starts the language server for the folder
