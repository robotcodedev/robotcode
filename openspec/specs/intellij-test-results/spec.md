# intellij-test-results Specification

## Purpose

Defines how the IntelliJ plugin turns the events of a Robot Framework run into the results shown in the run tab: the results tree, test statuses and messages, and the output that belongs to each test.

## Requirements

### Requirement: Results tree built from Robot Framework's events

The plugin SHALL show each suite and each test of a Robot Framework run in the results tree of the run tab as soon as it starts, below its parent suite. When a test ends, the tree SHALL show the status Robot Framework reports for it: passed, failed with Robot Framework's failure message, or skipped with its message, together with the test's duration.

#### Scenario: Run with a failing test

- **WHEN** a suite file with two passing tests and one test that fails with the message `intentional failure` is run
- **THEN** the results tree shows the file's suite with its three tests, two as passed and one as failed with the message `intentional failure`, each with its duration

### Requirement: Navigation from result nodes

Navigating from the node of a file suite SHALL open its file, and from a test node that passed or was skipped the line on which the test starts now, found by its full name.

#### Scenario: Passed test

- **WHEN** the user navigates from the node of a passed test after the run
- **THEN** the test's first line opens

#### Scenario: Lines added above the test

- **WHEN** lines were added above a test after the run, and the user navigates from that test's node
- **THEN** the line on which the test starts now opens

### Requirement: Results without console output

The results of a Robot Framework run SHALL reach the results tree also when the Robot Framework process writes nothing to its console.

#### Scenario: Process without console output

- **WHEN** `robot.toml` sets `console = "none"` and a suite file is run
- **THEN** the results tree shows all tests of the suite with their statuses

### Requirement: A failed or skipped suite teardown re-marks the suite's tests

When the suite teardown of a suite fails, the plugin SHALL show every test of that suite and of its child suites as failed, with the message Robot Framework reports for the test, also when the test was shown as passed before. When the suite teardown is skipped, the plugin SHALL show these tests as skipped with Robot Framework's message. The results tree, the run's status line and the gutter markers of the tests SHALL agree on the new status. This SHALL hold on every supported operating system.

#### Scenario: Failing suite teardown

- **WHEN** a suite file with the tests `First` and `Second`, which pass, and a `Suite Teardown` that fails with `teardown broke` is run
- **THEN** both tests are shown as failed with the message `Parent suite teardown failed:` followed by `teardown broke`
- **AND** the status line counts both tests as failed, and the gutter markers of both tests show the failed state

#### Scenario: Skipped suite teardown

- **WHEN** the `Suite Teardown` of that file calls `Skip` with `teardown skipped` instead
- **THEN** both tests are shown as skipped with the message `Skipped in parent suite teardown:` followed by `teardown skipped`

#### Scenario: Windows

- **WHEN** the suite file with the failing suite teardown is run on Windows
- **THEN** both tests are shown as failed, as on Linux and macOS

### Requirement: Console output in the order it was written, per test

The run console SHALL show the output of the Robot Framework process in the order the process wrote it, as a terminal shows it. Selecting a test in the results tree SHALL show the output the process wrote while that test ran, and no output written while another test ran. Output written while no test runs SHALL belong to the enclosing suite, or to the run itself when no suite runs.

#### Scenario: Order of the whole run

- **WHEN** a suite file with the tests `First` and `Second`, where each test calls `Log To Console` with `first console` and `second console`, is run
- **THEN** selecting the run's root node shows `first console` before the line of the test `Second` and before `second console`, in the order a terminal run of the same suite shows

#### Scenario: Output of one test

- **WHEN** the user selects the test `Second` after that run
- **THEN** the console shows `second console`, and no text that was written while `First` ran

#### Scenario: Warnings and errors under their test

- **WHEN** the test `First` logs `a warning` with level `WARN` and `an error` with level `ERROR`, and the user selects `First` after the run
- **THEN** the console shows the lines `[ WARN ] a warning` and `[ ERROR ] an error` that Robot Framework writes to its console, and selecting `Second` shows neither

#### Scenario: Repeated runs

- **WHEN** the same suite is run ten times in a row
- **THEN** every run shows the same order and the same output under each test

### Requirement: A run leaves no thread behind

After a Robot Framework run has ended, the plugin SHALL keep no thread alive that it started for the results of that run. Running many times in a row SHALL NOT increase the number of threads the IDE keeps.

#### Scenario: Several runs

- **WHEN** five runs of a suite have ended
- **THEN** no thread that served the results of these runs is still alive

### Requirement: Opening the report or the log after a run

When a run ends and the effective "Open output after run" value is "Report" or "Log", the plugin SHALL open the report or the log file that the run wrote in the target of "Open output target", for a file of the project through the IDE's built-in web server. Without JCEF, and for a browser that is no longer active, it SHALL use the default browser. With "Nothing", and when the run wrote no such file, it SHALL open nothing and report no error.

#### Scenario: Report after a run

- **WHEN** a configuration sets "Open output after run" to "Report", "Open output target" is "Built-in preview", and the run ends
- **THEN** the run's `report.html` opens in the IDE's built-in preview, with an http URL of the built-in web server

#### Scenario: Report in the default browser

- **WHEN** "Open output target" is "Default browser" and a run with "Open output after run" set to "Report" ends
- **THEN** the default browser receives the http URL of the run's `report.html` from the built-in web server, not a file URL

#### Scenario: A browser that is no longer configured

- **WHEN** "Open output target" names a browser that is no longer active in Settings | Tools | Web Browsers and Preview, and a run with "Open output after run" set to "Report" ends
- **THEN** the run's `report.html` opens in the default browser

#### Scenario: Default

- **WHEN** neither the configuration nor the project default changes "Open output after run" and the run ends
- **THEN** no file opens

#### Scenario: No log written

- **WHEN** "Open output after run" is "Log" and the robot arguments contain `--log NONE`
- **THEN** no file opens and no error is reported

### Requirement: Open Report and Open Log actions

The tab of a Robot Framework run, started with Run or with Debug, SHALL offer "Open Report" and "Open Log". Each SHALL be enabled once the run has reported that it wrote the file, and SHALL open the file in the target of "Open output target".

#### Scenario: Opening the log from the run tab

- **WHEN** a run of the test project has ended, "Open output target" is "Built-in preview", and the user clicks "Open Log" in its tab
- **THEN** the run's `log.html` opens in the built-in preview

#### Scenario: While the run is going

- **WHEN** a run is still going
- **THEN** "Open Report" and "Open Log" are disabled
