# Spec Delta

## ADDED Requirements

### Requirement: Problems in the startup phase are provisional

For the first 15 seconds after RobotCode first looks at a workspace folder, when VS Code starts or the folder is added, a problem of its Python environment SHALL count as provisional. A provisional problem SHALL get no environment message, the Testing view SHALL keep its loading state, and the language status SHALL show its items as busy, without an error. A problem that remains after the startup phase SHALL be shown at once.

#### Scenario: Environment selected late
- **WHEN** at startup RobotCode's first check finds the global interpreter without Robot Framework, and the Python side selects the folder's `.venv` with Robot Framework 8 seconds later
- **THEN** no environment message appears, the Testing view shows no hint about the environment, the language status shows no error, and the language server starts with `.venv`

#### Scenario: Problem that lasts
- **WHEN** the selected environment of the folder still has no Robot Framework 15 seconds after VS Code started
- **THEN** the environment message, the Testing view's hint and the language status's error appear at once

#### Scenario: Problem after the startup phase
- **WHEN** VS Code has run for a minute and the user selects an environment without Robot Framework for the folder
- **THEN** the Testing view's hint and the language status's error appear at once, and the environment message a few seconds later, as before
