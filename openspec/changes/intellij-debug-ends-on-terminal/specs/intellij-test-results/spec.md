## MODIFIED Requirements

### Requirement: Debug sessions show the "Terminal" tab

A Debug session of a Robot Framework run configuration SHALL show the same "Terminal" tab, selected when the session starts and again when it ends, next to its Debugger tab and its console, which SHALL be named "Debug Console" and SHALL show the results tree with the log messages per test, as a run does.

#### Scenario: The tabs when a debug session starts

- **WHEN** a Debug session of a Robot Framework run configuration starts
- **THEN** its "Terminal" tab is selected, and its console tab is named "Debug Console"

#### Scenario: Log message while debugging

- **WHEN** a test that calls `Log    should not in console` and `Log To Console    show in console` is debugged and stops at a breakpoint on a later line of the test
- **THEN** selecting the test in the "Debug Console" tab shows `should not in console`, and the "Terminal" tab shows `show in console`

#### Scenario: The tab when a debug session ends

- **WHEN** a Debug session of a Robot Framework run configuration has run its tests and ends
- **THEN** its "Terminal" tab is selected

#### Scenario: An error before the run

- **WHEN** the selection names the profile `typo`, which `robot.toml` does not define, and the user debugs a test
- **THEN** the session ends with its "Terminal" tab selected, which shows `Error: No profile matches 'typo'.`
