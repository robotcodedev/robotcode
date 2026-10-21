# Spec Delta

## ADDED Requirements

### Requirement: The language status marks the item with the problem

The Python item of RobotCode's language status SHALL be shown as an error only when the folder's Python interpreter has a problem: none is selected, it no longer exists or cannot be started, or it is older than Python 3.10. A missing or too old Robot Framework SHALL mark only the Robot Framework item as an error.

#### Scenario: Robot Framework missing
- **WHEN** the selected Python environment of the folder has Python 3.14 and no Robot Framework, and a Robot Framework file of the folder is open
- **THEN** the language status shows the Robot Framework item as an error and the Python item without one

#### Scenario: Interpreter missing
- **WHEN** the setting `robotcode.python` names an interpreter that does not exist
- **THEN** the language status shows the Python item as an error
