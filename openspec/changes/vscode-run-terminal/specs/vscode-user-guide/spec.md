# Spec Delta

## MODIFIED Requirements

### Requirement: Running and debugging in VS Code

The page Running and debugging SHALL explain with screenshots how to run and debug tests from the editor, with the icons beside the tests and with Run or Debug Current File, the `launch.json` configurations RobotCode offers, breakpoints, the Debug Console and inline values, where the output of a run appears and which console values there are, how to open the log after a run, and how to choose the configuration profiles for a run. It SHALL link to the Test Explorer page.

#### Scenario: Icons beside the tests
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** a screenshot shows the icons beside the tests in the editor that run or debug a test

#### Scenario: Link to the Test Explorer page
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** a link leads to `/guides/vscode/test-explorer/`

#### Scenario: Launch configurations
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** the page names every `launch.json` configuration RobotCode offers and what it is for

#### Scenario: Profiles for a run
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** the page shows how to choose configuration profiles with "RobotCode: Select Configuration Profiles"

#### Scenario: Output of a run
- **WHEN** a reader opens `/guides/vscode/running-and-debugging/`
- **THEN** the page explains that a run's output appears in RobotCode's run terminal, which shows the command line before each run, is reused and closes on a key, and names the console values `robotcodeTerminal`, `integratedTerminal`, `internalConsole` and `externalTerminal` with the setting `robotcode.debug.defaultConsole`
