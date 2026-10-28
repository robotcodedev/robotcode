# Spec Delta: vscode-python-environment

## MODIFIED Requirements

### Requirement: A later Robot Framework install is noticed

While the problem of a workspace folder that RobotCode has taken up is a missing or too old Robot Framework, the extension SHALL run its check script every few seconds, more slowly after a while, so that a Robot Framework installed in the meantime, wherever Python finds it, starts the language server without the user doing anything. It SHALL also check such a folder again on the environment events of both APIs.

#### Scenario: pip or uv install in a terminal

- **WHEN** the user runs `uv pip install robotframework`, `pip install robotframework` or `pip install --user robotframework` for the selected interpreter, or points `PYTHONPATH` at an install
- **THEN** within a few seconds the folder becomes usable and the language server starts

#### Scenario: Package events

- **WHEN** the Python Environments extension reports a package change for the folder's environment
- **THEN** the extension checks Robot Framework again

#### Scenario: Folder that RobotCode has not taken up

- **WHEN** RobotCode is active in a workspace folder that is no Robot Framework project and has no open Robot Framework document, and the folder's interpreter has no Robot Framework
- **THEN** the extension runs no check script for the folder, also not on the environment events of either API
