# Spec Delta

## ADDED Requirements

### Requirement: The language status marks the item with the problem

The Python item of RobotCode's language status SHALL be shown as an error exactly when the folder's interpreter has a problem: none is selected, it no longer exists or cannot be started, or it is older than Python 3.10. The Robot Framework item SHALL be shown as an error exactly when Robot Framework is missing or older than 5.0.

#### Scenario: Robot Framework missing
- **WHEN** the selected Python environment of the folder has Python 3.14 and no Robot Framework, and a Robot Framework file of the folder is open
- **THEN** the language status shows the Robot Framework item as an error and the Python item without one

#### Scenario: Interpreter missing
- **WHEN** the setting `robotcode.python` names an interpreter that does not exist
- **THEN** the language status shows the Python item as an error and the Robot Framework item without one

### Requirement: The Robot Framework item shows what the check knows

The Robot Framework item of the language status SHALL show the version that RobotCode's check of the environment found, also before the language server answers. While RobotCode cannot check Robot Framework, because the interpreter has a problem or the first check runs, the item SHALL show the version as unknown.

#### Scenario: Language server still starting
- **WHEN** the environment of the folder is usable with Robot Framework 7.5 and its language server has not answered yet
- **THEN** the Robot Framework item shows 7.5 without an error

#### Scenario: Interpreter missing
- **WHEN** the setting `robotcode.python` names an interpreter that does not exist
- **THEN** the Robot Framework item shows the version as unknown
