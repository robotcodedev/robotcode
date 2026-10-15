# Spec Delta

## ADDED Requirements

### Requirement: The results tree shows the debugger's log messages per test

Selecting a test in the results tree SHALL show the log messages that the RobotCode debugger sent while the test ran, in their order, each with its level unless the level is `INFO`, colored by level, and ending with a link to the file and line it was logged from where the debugger reports one; the test's failure details SHALL follow. Selecting a suite or the run SHALL show the messages of everything below it. The results tree SHALL NOT show the output of the Robot Framework process.

#### Scenario: A message of `Log` under its test

- **WHEN** a test that calls `Log    should not in console` and `Log To Console    show in console` is run, and the user selects the test
- **THEN** the console shows `should not in console` with a link to the line of the `Log` call, and does not show `show in console`

#### Scenario: Robot Framework's console switched off

- **WHEN** `robot.toml` sets `console = "none"`, a test that calls `Log    hello` is run, and the user selects the test
- **THEN** the console shows `hello`

#### Scenario: Warnings and errors under their test

- **WHEN** the test `First` logs `a warning` with level `WARN` and `an error` with level `ERROR`, the test `Second` logs nothing, and the user selects `First` after the run
- **THEN** the console shows `[ WARN ] a warning` in the color of warnings and `[ ERROR ] an error` in the color of errors, and selecting `Second` shows neither

#### Scenario: Trace level

- **WHEN** `robot.toml` sets `log-level = "TRACE"`, a test is run, and the user selects the test
- **THEN** the arguments and return values that Robot Framework logs at `TRACE` level appear under the test, and not in the "Terminal" tab

#### Scenario: Output log switched off

- **WHEN** a run configuration switches "Output log" off, a test that calls `Log    hello` is run, and the user selects the test
- **THEN** the console does not show `hello`

#### Scenario: Opening the location of a message

- **WHEN** the user clicks the link at the end of `should not in console`
- **THEN** the editor opens the test's file at the line of that `Log` call

### Requirement: Process output in a "Terminal" tab

The run window of every Robot Framework run SHALL show a "Terminal" tab first, selected when the run starts, and the results tree in a "Debug Console" tab after it. The "Terminal" tab SHALL show the output of the Robot Framework process in the order the process wrote it, as a terminal run of the same suite shows it, whatever is selected in the results tree. It SHALL NOT show the log messages that the results tree shows.

#### Scenario: The tabs when a run starts

- **WHEN** a Robot Framework run starts
- **THEN** its window shows the tabs "Terminal" and "Debug Console" in this order, with "Terminal" selected

#### Scenario: `Log` and `Log To Console`

- **WHEN** a test that calls `Log    should not in console` and `Log To Console    show in console` is run
- **THEN** the "Terminal" tab shows `show in console` and does not show `should not in console`

#### Scenario: Order of the whole run

- **WHEN** a suite file with the tests `First` and `Second`, where each test calls `Log To Console` with `first console` and `second console`, is run
- **THEN** the "Terminal" tab shows `first console` before the line of the test `Second` and before `second console`, in the order a terminal run of the same suite shows

#### Scenario: Warnings in both places

- **WHEN** a test logs `a warning` with level `WARN` and is run
- **THEN** the "Terminal" tab shows the line `[ WARN ] a warning` that Robot Framework writes to its console, and selecting the test in the results tree shows the message as well

#### Scenario: Repeated runs

- **WHEN** the same suite is run ten times in a row
- **THEN** every run shows the same order in the "Terminal" tab and the same messages under each test

### Requirement: Debug sessions show the "Terminal" tab

A Debug session of a Robot Framework run configuration SHALL show the same "Terminal" tab, selected when the session starts, next to its Debugger tab and its console, which SHALL be named "Debug Console" and SHALL show the results tree with the log messages per test, as a run does.

#### Scenario: The tabs when a debug session starts

- **WHEN** a Debug session of a Robot Framework run configuration starts
- **THEN** its "Terminal" tab is selected, and its console tab is named "Debug Console"

#### Scenario: Log message while debugging

- **WHEN** a test that calls `Log    should not in console` and `Log To Console    show in console` is debugged and stops at a breakpoint on a later line of the test
- **THEN** selecting the test in the "Debug Console" tab shows `should not in console`, and the "Terminal" tab shows `show in console`

## MODIFIED Requirements

### Requirement: Robot Framework's output files are links in the console

In the "Terminal" tab, each line in which Robot Framework names an output file, `Output:`, `Log:`, `Report:`, `XUnit:` or `Debug:` followed by the file's path, SHALL be a link. An HTML file SHALL open in the target of "Open output target", as with Open Report and Open Log, any other file in the editor. A line that names no file, such as `Output:  NONE`, SHALL stay plain text.

#### Scenario: Opening the report

- **WHEN** a run has ended, "Open output target" is "Built-in preview", and the user clicks the path in the `Report:` line of the "Terminal" tab
- **THEN** `report.html` opens in the built-in preview

#### Scenario: Opening the output file

- **WHEN** the user clicks the path in the `Output:` line of the "Terminal" tab
- **THEN** `output.xml` opens in the editor

#### Scenario: No output file

- **WHEN** `robot.toml` sets `output = "NONE"` and a run has ended
- **THEN** the `Output:  NONE` line of the "Terminal" tab is not a link

## REMOVED Requirements

### Requirement: Console output in the order it was written, per test

**Reason**: The process output moves to the "Terminal" tab, and the results tree shows the debugger's log messages per test instead, so that what a test shows no longer depends on Robot Framework's console options.

**Migration**: The "Terminal" tab keeps the order of the process output (requirement "Process output in a "Terminal" tab"); selecting a test shows its log messages (requirement "The results tree shows the debugger's log messages per test").
