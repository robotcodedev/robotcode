## MODIFIED Requirements

### Requirement: Discovery failures are reported

When discovery fails, because robotcode exits with an error or prints output that the plugin cannot read, the plugin SHALL keep the result of the last successful discovery, write the command line, the exit code and the complete output to idea.log, and not raise an IDE error. Unless the selection names a profile that `robot.toml` does not define, it SHALL show a RobotCode notification with the first lines of robotcode's error output and the actions "Retry" and, when the project folder has a `robot.toml`, "Open robot.toml".

#### Scenario: Syntax error in robot.toml

- **WHEN** the user saves robot.toml with a syntax error such as `output-dir = [`
- **THEN** one RobotCode notification shows robotcode's error about the invalid TOML file, the run markers of the last discovery stay, and idea.log gets no SEVERE entry from RobotCode

#### Scenario: Retry

- **WHEN** the user clicks "Retry" in the notification
- **THEN** a full discovery runs

## ADDED Requirements

### Requirement: A discovery that fails because of the selection reports the selection

When discovery fails while the project's selection names a profile or pattern that selects no profile of `robot.toml`, the plugin SHALL show the notification about the selected profile instead of the notification about the failed discovery.

#### Scenario: Selection with a renamed profile

- **WHEN** `dev` is selected, `robot.toml` renames it to `development`, and discovery runs
- **THEN** one notification names `dev`, with "Remove from Selection" and "Select Configuration Profiles...", and no notification about the failed discovery appears
