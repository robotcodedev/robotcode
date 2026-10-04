# Spec Delta

## Purpose

Defines how the IntelliJ plugin turns the events of a Robot Framework run into the results shown in the run tab: the results tree, test statuses and messages, and the output that belongs to each test.

## ADDED Requirements

### Requirement: Results tree built from Robot Framework's events

The plugin SHALL show each suite and each test of a Robot Framework run in the results tree of the run tab as soon as it starts, below its parent suite. When a test ends, the tree SHALL show the status Robot Framework reports for it: passed, failed with Robot Framework's failure message, or skipped with its message, together with the test's duration. Navigating from a suite node, or from a test node that passed or was skipped, SHALL open its source line. The results SHALL reach the tree also when the Robot Framework process writes nothing to its console.

#### Scenario: Run with a failing test

- **WHEN** a suite file with two passing tests and one test that fails with the message `intentional failure` is run
- **THEN** the results tree shows the file's suite with its three tests, two as passed and one as failed with the message `intentional failure`, each with its duration
- **AND** navigating from a passed test node opens the test's first line

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
