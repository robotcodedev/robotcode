## ADDED Requirements

### Requirement: The Debug Console stays closed for a run in a terminal

When a run or debug session writes its output to a terminal (`robotcodeTerminal`, `integratedTerminal` or `externalTerminal`), VS Code SHALL NOT open the Debug Console by itself. Two values still decide:
- `internalConsoleOptions` set in the launch configuration;
- `debug.internalConsoleOptions` set by the user in user, workspace or folder settings.

With `internalConsole`, VS Code SHALL behave as before.

#### Scenario: First run of a window

- **WHEN** neither the launch configuration nor the user sets an `internalConsoleOptions` value, and the user runs a test from the Test Explorer as the first run after the window opened
- **THEN** the panel shows RobotCode's run terminal, and VS Code does not switch it to the Debug Console

#### Scenario: First debug session of a window

- **WHEN** neither the launch configuration nor the user sets an `internalConsoleOptions` value, and the user debugs a test as the first session after the window opened
- **THEN** the panel shows RobotCode's run terminal, and VS Code does not switch it to the Debug Console

#### Scenario: Launch configuration sets the value

- **WHEN** a launch configuration with `"internalConsoleOptions": "openOnSessionStart"` is started with `robotcodeTerminal`
- **THEN** VS Code opens the Debug Console at the start of each of its runs

#### Scenario: User sets the value

- **WHEN** the user settings contain `"debug.internalConsoleOptions": "openOnFirstSessionStart"` and the user runs a test with `robotcodeTerminal` as the first run after the window opened
- **THEN** VS Code opens the Debug Console, as before this change

#### Scenario: Internal console

- **WHEN** the console of a run is `internalConsole` and the user runs a test as the first run after the window opened
- **THEN** VS Code opens the Debug Console, as before this change
