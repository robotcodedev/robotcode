# Spec Delta

## ADDED Requirements

### Requirement: Run markers only with a usable interpreter

When the result of the check of the project's interpreter becomes not usable, a problem or a failed check, the plugin SHALL remove the run markers of the project's tests and suites. When the interpreter becomes usable again, the markers SHALL appear again after the discovery that then runs. While a check is running, the markers SHALL stay as they are.

#### Scenario: Robot Framework removed from the interpreter

- **WHEN** a Robot Framework file shows run markers, and the project is switched to an interpreter without Robot Framework
- **THEN** the run markers disappear from the open file, and the banner says that Robot Framework is not installed

#### Scenario: Check failed

- **WHEN** a Robot Framework file shows run markers, and the check of a newly chosen interpreter times out
- **THEN** the run markers disappear, and the banner says that the check failed

#### Scenario: Usable again

- **WHEN** the markers were removed because Robot Framework was missing, and Robot Framework is then installed and the interpreter's paths are refreshed
- **THEN** discovery runs, and the run markers appear again without reopening the file

#### Scenario: Switching between usable interpreters

- **WHEN** the project is switched from one usable interpreter to another
- **THEN** the run markers stay while the new interpreter is checked
