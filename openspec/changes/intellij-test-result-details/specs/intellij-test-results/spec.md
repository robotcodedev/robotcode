# Spec Delta

## Purpose

Defines how the IntelliJ plugin turns the events of a Robot Framework run into the results shown in the run tab: the results tree, test statuses and failure details, the output of each test, and the actions that work on these results.

## ADDED Requirements

### Requirement: Failure details list the failed keywords

When a test fails in a keyword, the plugin SHALL show below the test's failure message the keywords that failed, innermost first. Each entry SHALL name the keyword, with its library or resource where Robot Framework reports one, and the file and line where the keyword was called. Each location SHALL be a link that opens the file at that line.

#### Scenario: Failure in a keyword of a resource file

- **WHEN** the test `Third Test Fails` in `tests/sample.robot` calls the keyword `Build Greeting` of `resources/common.resource`, and `Should Be Equal` fails inside it
- **THEN** selecting the test shows its failure message, then `Should Be Equal` with `resources/common.resource` and the line of that call, then `Build Greeting` with `tests/sample.robot` and the line of that call

#### Scenario: Opening a location

- **WHEN** the user clicks the location of `Should Be Equal` in these failure details
- **THEN** `resources/common.resource` opens at the line of the `Should Be Equal` call

#### Scenario: Paths with spaces

- **WHEN** the project folder's path contains spaces and a test fails in a keyword
- **THEN** every location in the failure details is a complete link to its file and line

### Requirement: Navigating from a failed test

Navigating from a failed test whose failure details list failed keywords SHALL open the call of the innermost failed keyword. A failed test without failed keywords, for example one that failed in its suite setup or suite teardown, SHALL show its message only and SHALL navigate to its own line.

#### Scenario: Navigating from the failed test

- **WHEN** the user navigates to the source of `Third Test Fails` from the results tree
- **THEN** the editor opens `resources/common.resource` at the line of the `Should Be Equal` call

#### Scenario: Failure in the suite setup

- **WHEN** a test fails because the suite setup of its suite failed
- **THEN** selecting the test shows only its failure message, and navigating from it opens the test's own line

### Requirement: The run's test count is known from the start

When a run starts, the run tab SHALL know how many tests and tasks the run executes, and its progress SHALL show the finished tests out of that total while the run proceeds. Tests that Robot Framework leaves out of the run, for example through tag options in `robot.toml`, SHALL not count.

#### Scenario: Progress of a suite

- **WHEN** a suite file with three tests is run
- **THEN** the run tab shows a total of three tests while the first test runs, and the progress reaches three of three when the run ends

#### Scenario: Run of one test

- **WHEN** a single test is run from its gutter marker
- **THEN** the run tab shows a total of one test

### Requirement: Robot Framework's output files are links in the console

In the run console, each line in which Robot Framework names an output file, `Output:`, `Log:`, `Report:`, `XUnit:` or `Debug:` followed by the file's path, SHALL be a link. An HTML file SHALL open in the browser, any other file in the editor. A line that names no file, such as `Output:  NONE`, SHALL stay plain text.

#### Scenario: Opening the report

- **WHEN** a run has ended and the user clicks the path in the `Report:` line of the console
- **THEN** `report.html` opens in the browser

#### Scenario: Opening the output file

- **WHEN** the user clicks the path in the `Output:` line
- **THEN** `output.xml` opens in the editor

#### Scenario: No output file

- **WHEN** `robot.toml` sets `output = "NONE"` and a run has ended
- **THEN** the `Output:  NONE` line of the console is not a link

### Requirement: Rerun Failed Tests reruns exactly the failed tests

After a run in which tests failed, the "Rerun Failed Tests" action of the run tab SHALL be enabled. It SHALL run exactly the failed tests and tasks of that run, including those that failed through their suite teardown, with the other settings of the run configuration, in the same tab, and with the same executor, Run or Debug. After a run without failed tests, the action SHALL be disabled.

#### Scenario: Rerunning one failed test

- **WHEN** `tests/sample.robot` was run and only `Third Test Fails` failed, and the user chooses "Rerun Failed Tests"
- **THEN** only `Third Test Fails` runs, in the same tab

#### Scenario: Tests failed through the suite teardown

- **WHEN** both tests of a suite failed because its suite teardown failed, and the user chooses "Rerun Failed Tests"
- **THEN** both tests and the suite teardown run again

#### Scenario: Rerunning a debug session

- **WHEN** the run with failed tests was a Debug session and the user chooses "Rerun Failed Tests"
- **THEN** a Debug session runs only the failed tests and stops at their breakpoints

#### Scenario: Nothing failed

- **WHEN** every test of the run passed
- **THEN** "Rerun Failed Tests" is disabled
