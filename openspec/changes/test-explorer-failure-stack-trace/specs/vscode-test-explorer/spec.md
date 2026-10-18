# Spec Delta

## ADDED Requirements

### Requirement: One entry per failure of a test

When a test or task fails in its keywords, the Test Explorer SHALL show one entry for each of its failures, in the order they occurred. Each entry SHALL carry the message of its failure and sit at the call in the test that led to it: a step of the test, or its setup or teardown. Each entry SHALL list the deeper calls that led to the failure, innermost first, each with its file and line.

#### Scenario: Failure in a keyword of a resource file

- **WHEN** the test `Login Works` in `tests/login.robot` calls `Welcome Message Should Be` of `resources/shop.resource` in line 16, and `Should Be Equal` fails inside it
- **THEN** Test Results shows one entry for `Login Works`, with the message of `Should Be Equal`, which sits at line 16 of `login.robot` and lists the call of `Should Be Equal` in `shop.resource` with its line

#### Scenario: Opening the entry from the test file

- **WHEN** the user clicks the marker of this entry at line 16 of `login.robot`
- **THEN** the view of the entry opens below line 16, with the message and, below it, the call of `Should Be Equal` with a few lines of the code of `shop.resource`

#### Scenario: Opening the entry from the resource file

- **WHEN** the user clicks the marker of this entry at the call of `Should Be Equal` in `shop.resource`
- **THEN** `login.robot` opens with the view of the entry below line 16

#### Scenario: Going to the error from Test Results

- **WHEN** the user clicks **Go to Error** at this entry in Test Results
- **THEN** `login.robot` opens at line 16

#### Scenario: Several failures collected

- **WHEN** a test runs `Check Value    1` and `Check Value    2` with `Run Keyword And Continue On Failure`, and both fail
- **THEN** Test Results shows two entries for the test, first the one of `Check Value    1`, each with the message of its own failure and at the line of its own step

#### Scenario: Failure in the body and in the teardown

- **WHEN** a step of a test fails, and then its teardown fails as well
- **THEN** the test has two entries, the first at the failed step and the second at the line of `[Teardown]`, each with the message of its own failure

#### Scenario: Failure in a step

- **WHEN** a step of the test calls `Should Be Equal` itself, and it fails
- **THEN** the entry sits at that step and lists no deeper calls

### Requirement: Caught failures are marked

When a failed test or task caught a failure, with `TRY`/`EXCEPT` or with a BuiltIn keyword that handles failures such as `Run Keyword And Ignore Error`, the Test Explorer SHALL show the caught failure as an entry of its own, after the entries of the failures that made the test fail. The entry's text SHALL be `Caught: ` followed by the failure's message; it SHALL sit at and list its calls like the other entries.

#### Scenario: Failure caught by TRY/EXCEPT

- **WHEN** a test catches the failure of `Should Be Equal    a    b` in a `TRY` branch with `EXCEPT`, and later fails in `Check Value`
- **THEN** the test has the entry of the failure in `Check Value` first, then the entry `Caught: a != b` at the line of the `Should Be Equal` step

#### Scenario: EXCEPT branch that fails

- **WHEN** a step in a `TRY` branch fails, and the step in its `EXCEPT` branch fails as well
- **THEN** the test has two entries, neither of them starting with `Caught: `

#### Scenario: Passed test

- **WHEN** a test catches a failure with `Run Keyword And Ignore Error` and passes
- **THEN** Test Results shows the test as passed, without an entry

### Requirement: Calls without a marker show the failure inline

VS Code marks an entry in the editor once in each file: at the line where it sits, and in every other file at its innermost call there. Every other call that an entry lists SHALL show the entry's text as inline output at the end of its line while VS Code's **Show Inline Test Output** is switched on, and the test's output SHALL contain the entry's text once for each of these calls.

#### Scenario: Nested calls in one resource file

- **WHEN** the test `Nested` calls `Outer In Resource` in line 6 of `suite.robot`, which calls `Inner In Resource` in line 3 of `shop.resource`, which calls `Check Value` in line 6, in which `Should Be Equal` in line 10 fails with `0 != ok`
- **THEN** the editor marks line 6 of `suite.robot` and line 10 of `shop.resource` with `0 != ok`, and lines 3 and 6 of `shop.resource` show `0 != ok` as inline output

#### Scenario: Inline test output switched off

- **WHEN** the user switches **Show Inline Test Output** off in the Testing view and runs the test `Nested` again
- **THEN** only line 6 of `suite.robot` and line 10 of `shop.resource` show `0 != ok`

### Requirement: A failed test without a failed keyword shows its message

When a test or task fails without a failure in one of its keywords, the Test Explorer SHALL show the test's message as an entry at the test's own line.

#### Scenario: Failed suite setup

- **WHEN** the suite setup of `login.robot` fails
- **THEN** each test of the suite has one entry, with its message that the parent suite setup failed, at the line of the test
