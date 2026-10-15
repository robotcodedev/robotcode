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

When a run ends and the effective "Open output after run" value is "Report" or "Log", the plugin SHALL open the report or the log file that the run wrote in the target of "Open output target"; a browser SHALL get a file of the project through the IDE's built-in web server. Without JCEF, and for a browser that is no longer active, it SHALL use the default browser. With "Nothing", and when the run wrote no such file, it SHALL open nothing and report no error.

#### Scenario: Report after a run

- **WHEN** a configuration sets "Open output after run" to "Report", "Open output target" is "Built-in preview", and the run ends
- **THEN** the run's `report.html` opens in a RobotCode preview tab of the IDE

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

### Requirement: The preview tab of an output file is reused

Opening a report or a log in the built-in preview SHALL show it in a RobotCode preview tab of that file. When that tab is open, a later open of the file SHALL load its current content into that tab and bring the tab to the front in the editor split where it is; it SHALL NOT close the tab or open a second one. This SHALL hold for files inside and outside the project.

#### Scenario: Another run with the preview beside the editor

- **WHEN** the preview tab of `report.html` was moved to the right editor split, the test is changed in the left split, and the configuration runs again three times
- **THEN** after each run the tab in the right split shows the report of that run, the left split still shows only the test and stays the active split, and no second preview tab of `report.html` exists

#### Scenario: Output outside the project

- **WHEN** the output directory of a configuration is outside the project and the configuration runs twice with "Open output after run" set to "Report"
- **THEN** after the second run the preview tab shows the report of the second run

### Requirement: Toolbar of the preview tab

The preview tab SHALL have a toolbar with Back and Forward through the pages shown in the tab, enabled only when there is such a page, Reload of the shown page, Find in Page, which highlights the matches of a text and moves between them, and Open in Browser, which opens the shown page in the default browser as the target "Default browser" does. Loading the tab's file again after a run SHALL NOT add a page to the tab's history.

#### Scenario: Back from the log to the report

- **WHEN** the user clicks a link to the log in the report's preview tab and then Back
- **THEN** the tab shows the report again, and Forward is enabled

#### Scenario: Reloading the shown page

- **WHEN** a configuration with "Open output after run" set to "Nothing" ran again while the report's preview tab was open, and the user clicks Reload
- **THEN** the tab shows the report of the last run

#### Scenario: Another run adds no history

- **WHEN** the report's preview tab is open, the user did not follow a link, and the configuration runs again
- **THEN** Back stays disabled

#### Scenario: Opening the shown page in a browser

- **WHEN** the tab shows the log after a click on a link in the report, and the user clicks Open in Browser
- **THEN** the default browser receives the http URL of `log.html` from the built-in web server

#### Scenario: Finding text

- **WHEN** the user opens Find in Page and types the name of a test
- **THEN** the matches in the page are highlighted, and Enter moves to the next one

### Requirement: Failure details list the failed keywords

When a test fails in a keyword, the plugin SHALL show below the test's failure message the keywords that failed, innermost first. Each entry SHALL name the keyword, with its library or resource where Robot Framework reports one, and the file and line where the keyword was called. Each location SHALL be a link that opens the file at that line. Failures that the test caught before, which Robot Framework's log keeps collapsed, SHALL follow, marked as caught.

#### Scenario: Failure in a keyword of a resource file

- **WHEN** the test `Third Test Fails` in `tests/sample.robot` calls the keyword `Build Greeting` of `resources/common.resource`, and `Should Be Equal` fails inside it
- **THEN** selecting the test shows its failure message, then `Should Be Equal` with `resources/common.resource` and the line of that call, then `Build Greeting` with `tests/sample.robot` and the line of that call

#### Scenario: Opening a location

- **WHEN** the user clicks the location of `Should Be Equal` in these failure details
- **THEN** `resources/common.resource` opens at the line of the `Should Be Equal` call

#### Scenario: Paths with spaces

- **WHEN** the project folder's path contains spaces and a test fails in a keyword
- **THEN** every location in the failure details is a complete link to its file and line

#### Scenario: A failure that was caught earlier

- **WHEN** a test catches a failing keyword, with `TRY`/`EXCEPT` or `Run Keyword And Ignore Error`, and later fails in another keyword
- **THEN** the failure details list the keywords of the later failure first, then the caught keyword, marked as caught

### Requirement: Navigating from a failed test

Navigating from a failed test whose failure details list failed keywords SHALL open the call of the innermost failed keyword that is not marked as caught. A failed test without failed keywords, for example one that failed in its suite setup or suite teardown, SHALL show its message only. A failed test without failed keywords other than caught ones SHALL navigate to its own line.

#### Scenario: Navigating from the failed test

- **WHEN** the user navigates to the source of `Third Test Fails` from the results tree
- **THEN** the editor opens `resources/common.resource` at the line of the `Should Be Equal` call

#### Scenario: Navigating past a caught failure

- **WHEN** a test caught a failing `Should Be Equal` with `TRY`/`EXCEPT` and then failed in the keyword `Check Value`
- **THEN** navigating from the test opens the call that failed inside `Check Value`

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

In the run console, each line in which Robot Framework names an output file, `Output:`, `Log:`, `Report:`, `XUnit:` or `Debug:` followed by the file's path, SHALL be a link. An HTML file SHALL open in the target of "Open output target", as with Open Report and Open Log, any other file in the editor. A line that names no file, such as `Output:  NONE`, SHALL stay plain text.

#### Scenario: Opening the report

- **WHEN** a run has ended, "Open output target" is "Built-in preview", and the user clicks the path in the `Report:` line of the console
- **THEN** `report.html` opens in the built-in preview

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

#### Scenario: Rerunning after a run of a folder

- **WHEN** a configuration whose target is the folder `tests` ran, only `Third Test Fails` failed, and the user chooses "Rerun Failed Tests"
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
