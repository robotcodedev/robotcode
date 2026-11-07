# results-compare Specification

## Purpose

Defines how `robotcode results compare` puts two or more result files side by side: the counts of each run, the status of each test over the runs, shared failures, growing elapsed times, run messages and environments, and how runs are named, ordered and grouped.

## Requirements

### Requirement: Runs from the arguments

`robotcode results compare` SHALL take two or more runs as arguments. A run is the path of a result file, or `NAME=PATH` to give it a name. An argument that names an existing file SHALL always be a path, even if it contains `=`. Fewer than two runs or a result file that doesn't exist SHALL be an error.

#### Scenario: Two paths
- **WHEN** `robotcode results compare run1/output.xml run2/output.xml` runs
- **THEN** both runs are compared, as `#1` and `#2`

#### Scenario: Named runs
- **WHEN** `robotcode results compare linux=out/linux.xml windows=out/win.xml` runs
- **THEN** the runs are called `linux` and `windows` in the output

#### Scenario: A file name with an equals sign
- **WHEN** `robotcode results compare a=b.xml other.xml` runs, where `a=b.xml` is an existing file
- **THEN** `a=b.xml` is compared as a run without a name

#### Scenario: Only one run
- **WHEN** `robotcode results compare run1/output.xml` runs
- **THEN** robotcode reports that `compare` needs at least two runs
- **AND** the process exits with code 128

#### Scenario: Missing result file
- **WHEN** `robotcode results compare run1/output.xml linux=missing.xml` runs, where `missing.xml` doesn't exist
- **THEN** robotcode reports that `missing.xml` was not found
- **AND** the process exits with code 128

### Requirement: Names are unique

Two runs SHALL NOT have the same name. A repeated name SHALL be an error that names it.

#### Scenario: Repeated name
- **WHEN** `robotcode results compare linux=a.xml linux=b.xml` runs
- **THEN** robotcode reports that the name `linux` is given twice
- **AND** the process exits with code 128

### Requirement: Tests are matched by their full name

`robotcode results compare` SHALL treat tests with the same full name in different runs as the same test, as `results diff` does.

#### Scenario: Same test in two runs
- **WHEN** two runs both contain `Shop.Checkout.Pay`
- **THEN** `--show tests` shows one row for `Shop.Checkout.Pay` with its status in both runs

### Requirement: Overview of the runs

`robotcode results compare` SHALL always show an overview first, one row per run: its number, its name when it has one, its path, its start time, and its numbers of tests, passed, failed and skipped tests and its elapsed time. Without `--by` and `--show`, it SHALL show only the overview.

#### Scenario: Overview only
- **WHEN** `robotcode results compare run1/output.xml run2/output.xml run3/output.xml` runs
- **THEN** the output is one table with the rows `#1`, `#2` and `#3`, each with the counts and the elapsed time of its run

#### Scenario: Overview with a view
- **WHEN** `robotcode results compare run1/output.xml run2/output.xml --show tests` runs
- **THEN** the overview comes first and the status per test follows

### Requirement: Order of the runs

The runs SHALL be in the order of the arguments. With `--run-order start-time` they SHALL be in the order of the start time of their top suite. For a file whose top suite has no start time, as after `rebot` merged several files, the earliest start of its suites SHALL count. Runs without any start time SHALL come last, in the order of the arguments.

#### Scenario: Argument order
- **WHEN** `robotcode results compare new.xml old.xml` runs, where `old.xml` started earlier
- **THEN** `new.xml` is `#1` and `old.xml` is `#2`

#### Scenario: Start time
- **WHEN** `robotcode results compare new.xml old.xml --run-order start-time` runs, where `old.xml` started earlier
- **THEN** `old.xml` is `#1` and `new.xml` is `#2`

#### Scenario: File merged by rebot
- **WHEN** `--run-order start-time` orders a file that `rebot` merged from two outputs
- **THEN** the file is placed by the earlier start of the two merged runs

### Requirement: The last runs

With `--last N`, `robotcode results compare` SHALL keep only the last N runs in their order and leave the others out of every view.

#### Scenario: Last three of five
- **WHEN** `robotcode results compare r1.xml r2.xml r3.xml r4.xml r5.xml --last 3` runs
- **THEN** only `r3.xml`, `r4.xml` and `r5.xml` are compared, as `#3`, `#4` and `#5`

### Requirement: Filters apply to every run

The filters of `results diff`, such as `--include`, `--suite`, `--test` and `--search`, SHALL apply to every run before the runs are compared.

#### Scenario: Tag filter
- **WHEN** `robotcode results compare r1.xml r2.xml --include smoke` runs
- **THEN** every view counts and lists only the tests tagged `smoke`

### Requirement: Counts per tag or suite

With `--by tag` or `--by suite`, repeatable, `robotcode results compare` SHALL add one table per dimension: one row per tag or suite and one column per run, each cell with the failed and the total tests of that group in that run. `--sort` SHALL sort the rows by `name`, `total`, `failed` or `elapsed` in the last run.

#### Scenario: Counts per tag
- **WHEN** `robotcode results compare r1.xml r2.xml --by tag` runs, where 2 of the 20 `smoke` tests fail in `r2.xml` and none in `r1.xml`
- **THEN** the row `smoke` shows `0/20` for `#1` and `2/20` for `#2`

#### Scenario: Both dimensions
- **WHEN** `robotcode results compare r1.xml r2.xml --by tag --by suite` runs
- **THEN** a table per tag and a table per suite follow the overview

### Requirement: Views

`--show`, repeatable, SHALL add the views `tests`, `failures`, `elapsed`, `messages` and `environment` after the overview and the tables of `--by`, in the order given. A view given twice SHALL be shown once.

#### Scenario: Two views
- **WHEN** `robotcode results compare r1.xml r2.xml --show elapsed --show tests` runs
- **THEN** the overview, the elapsed view and the status per test follow each other in that order

#### Scenario: Unknown view
- **WHEN** `robotcode results compare r1.xml r2.xml --show nope` runs
- **THEN** robotcode reports the invalid value of `--show`
- **AND** the process exits with code 128

### Requirement: Limit of rows

`--top N` SHALL limit every table of `--by` and every view except `environment` to N rows and say how many rows were left out. `--top 0`, the default, SHALL show all rows.

#### Scenario: Top five tests
- **WHEN** `robotcode results compare r1.xml r2.xml --show tests --top 5` runs, where 8 tests failed in a run
- **THEN** the status per test shows 5 tests and says that 3 more were left out

### Requirement: Status of each test over the runs

`--show tests` SHALL list every test that failed in at least one run, with its status in each run as one ASCII character: `P` passed, `F` failed, `S` skipped, `N` not run, `-` for a run without the test. It SHALL show the failed count out of the runs that had the test, and sort the tests by that count, most first.

#### Scenario: A test added later
- **WHEN** `--show tests` compares ten runs, where `Shop.Checkout.Pay` exists from run 5 on and failed in run 7
- **THEN** its status is `----PPFPPP`
- **AND** its failed count is `1/6`

#### Scenario: Tests that never failed
- **WHEN** `--show tests` compares runs where a test passed or was skipped in every run
- **THEN** the test is not listed

### Requirement: Flaky tests

`--show tests` SHALL mark a test as flaky when its status changes between passed and failed at least twice over the runs, with skipped runs and runs without the test left out. A single change is a new failure or a fix, not flakiness.

#### Scenario: Flaky
- **WHEN** a test has the status `PFPPFP`
- **THEN** it is marked as flaky

#### Scenario: Failing from one run on
- **WHEN** a test has the status `PPPFFF`
- **THEN** it is not marked as flaky

#### Scenario: Skips in between
- **WHEN** a test has the status `PSF` over three runs
- **THEN** it is not marked as flaky

### Requirement: Failing since

For a test that failed in the last run that had it, `--show tests` SHALL name the run where its uninterrupted series of failures up to that run began. Runs without the test SHALL NOT interrupt the series.

#### Scenario: Failing since run 4
- **WHEN** a test has the status `PPPFFF`
- **THEN** it is failing since `#4`

#### Scenario: Gap in the series
- **WHEN** a test has the status `PPF-FF`
- **THEN** it is failing since `#3`

#### Scenario: Passed in the last run
- **WHEN** a test has the status `PPFFFP`
- **THEN** no run is named as failing since

### Requirement: The same failure over tests and runs

`--show failures` SHALL group the messages of failed tests over all runs, two messages counting as the same when their texts are equal after every number is replaced by `#` and runs of whitespace are collapsed. Each group SHALL show one of its messages, its number of tests, its count of tests per run, and the first run it appears in, sorted by the number of tests, most first.

#### Scenario: Numbers differ
- **WHEN** one test fails with `500 Server Error for url: http://shop/order/4711` and another with `500 Server Error for url: http://shop/order/4712`
- **THEN** both are one group with 2 tests

#### Scenario: First run of a failure
- **WHEN** a message appears in runs 3 to 5 of five runs
- **THEN** its group names `#3` as the first run

#### Scenario: Message length
- **WHEN** `--show failures --message-chars 40` runs
- **THEN** every shown message is cut to 40 characters

### Requirement: Growth of elapsed times

`--show elapsed` SHALL list tests and suites whose elapsed time in the last run that had them is longer than the median of their elapsed times in the runs before it that had them. It SHALL show the median, the last time and the growth in seconds and percent, sorted by the growth in seconds, most first. An item in fewer than two runs SHALL NOT be listed.

#### Scenario: Slower in the last run
- **WHEN** a test took 10, 11, 30 and 12 seconds in four runs and 20 seconds in the fifth
- **THEN** it is listed with the median 11.5 seconds, the last time 20 seconds and the growth 8.5 seconds

#### Scenario: Faster in the last run
- **WHEN** a test took 10 seconds in four runs and 8 seconds in the fifth
- **THEN** it is not listed

### Requirement: Messages of the runs

`--show messages` SHALL show the error and warning messages that each run lists as its execution errors, as `log.html` does, grouped by level and by text as in `--show failures`: the count per level and run, and per message its count per run and the first and last run it appears in. A message only in the last run SHALL be marked as new, one missing from the last run as gone.

#### Scenario: New warning
- **WHEN** a deprecation warning appears only in the last of three runs
- **THEN** it is marked as new with the first run `#3`

#### Scenario: Gone error
- **WHEN** an import error appears in runs 1 and 2 of three runs
- **THEN** it is marked as gone with the last run `#2`

### Requirement: Environment of the runs

`--show environment` SHALL show one row per run with the tool that wrote the file and its version, the Python version and the platform, as the file records them, and one column per metadata name of the top suites. It SHALL show them for every supported Robot Framework version.

#### Scenario: Versions and metadata
- **WHEN** `--show environment` compares a run of Robot Framework 7.5 on Python 3.14.9 on Linux, started with `--metadata Browser:chrome`, and one of Robot Framework 7.4 without metadata
- **THEN** the first row shows `Robot 7.5`, `3.14.9`, `linux` and `chrome` under `Browser`, the second row `Robot 7.4` and an empty `Browser`

#### Scenario: File written by rebot
- **WHEN** a file was written by `rebot` of Robot Framework 7.5
- **THEN** its row shows `Rebot 7.5`, not the version of the run

#### Scenario: Older Robot Framework
- **WHEN** `--show environment` runs with Robot Framework 5.0 installed
- **THEN** it shows the versions recorded in each file

### Requirement: Groups of runs

With `--group-by-metadata NAME`, runs with the same value of the metadata `NAME` in their top suite SHALL form a group, and runs without it a group of their own. The runs of a group SHALL stand together, the groups in the order of their first run. The overview SHALL show the group of each run and a sum row per group.

#### Scenario: Two platforms
- **WHEN** `robotcode results compare l1.xml w1.xml l2.xml w2.xml --group-by-metadata Platform` runs, where `l1.xml` and `l2.xml` have `Platform` `linux` and the others `windows`
- **THEN** the runs are in the order `l1.xml`, `l2.xml`, `w1.xml`, `w2.xml`
- **AND** the overview has a sum row for `linux` and one for `windows`

#### Scenario: Run without the metadata
- **WHEN** one run has no metadata `Platform`
- **THEN** it forms a group of its own

### Requirement: Values that depend on the order are computed per group

With groups, `robotcode results compare` SHALL compute every value that depends on the order of the runs within each group: the failed count, flaky tests and failing since in `--show tests`, the growth in `--show elapsed`, the first run in `--show failures`, and new and gone in `--show messages`. `--last N` SHALL keep the last N runs of each group. The status of a test SHALL have a space between groups.

#### Scenario: Fails only on one platform
- **WHEN** a test passed in all five `linux` runs and failed in four of the five `windows` runs
- **THEN** its status is `PPPPP FFPFF`
- **AND** its failed count is shown per group as `0/5 · 4/5`

#### Scenario: Last runs per group
- **WHEN** `--group-by-metadata Platform --last 2` compares five runs per platform
- **THEN** the last two runs of each platform are compared

### Requirement: Same views in JSON

With `-f json`, `robotcode results compare` SHALL give the same runs and views as the text output, with one value per run as a list entry, `null` for a run without the test, suite or message, and the failed count and the status of each test as numbers and status names.

#### Scenario: Status per test in JSON
- **WHEN** `robotcode -f json results compare r1.xml r2.xml r3.xml --show tests` runs, where a test exists only in `r2.xml` and `r3.xml`
- **THEN** its statuses are `null`, `"PASS"` and `"FAIL"`

### Requirement: Exit code

`robotcode results compare` SHALL exit with 0 when it has compared the runs, whatever it found. An error that stops it SHALL exit with 128, as for every `results` command.

#### Scenario: Failed tests
- **WHEN** `robotcode results compare r1.xml r2.xml` runs, where tests failed in both runs
- **THEN** the process exits with code 0

#### Scenario: Broken file
- **WHEN** `robotcode results compare r1.xml broken.xml` runs, where `broken.xml` is no result file
- **THEN** the process exits with code 128
