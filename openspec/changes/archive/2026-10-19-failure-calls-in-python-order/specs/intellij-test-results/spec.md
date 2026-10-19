# Spec Delta

## MODIFIED Requirements

### Requirement: Failure details list the failed keywords

When a test fails in its keywords, the plugin SHALL show below the test's failure message each failure with its calls as Python lists them, from the call in the test inward, each as `File "<file>", line <line>, in <keyword>`, the keyword with its library or resource where reported. Each location SHALL be a link that opens the file at that line. Several uncaught failures SHALL follow an empty line and each begin with the first line of its message; caught ones SHALL follow, marked as caught.

#### Scenario: Failure in a keyword of a resource file

- **WHEN** the test `Third Test Fails` in `tests/sample.robot` calls the keyword `Build Greeting` of `resources/common.resource`, and `Should Be Equal` fails inside it
- **THEN** selecting the test shows its failure message, then the line of the call of `Build Greeting` in `tests/sample.robot`, then the line of the call of `Should Be Equal` in `resources/common.resource`, each in the form `File "<file>", line <line>, in <keyword>`

#### Scenario: Opening a location

- **WHEN** the user clicks the location of `Should Be Equal` in these failure details
- **THEN** `resources/common.resource` opens at the line of the `Should Be Equal` call

#### Scenario: Paths with spaces

- **WHEN** the project folder's path contains spaces and a test fails in a keyword
- **THEN** every location in the failure details is a complete link to its file and line

#### Scenario: A failure that was caught earlier

- **WHEN** a test catches a failing keyword, with `TRY`/`EXCEPT` or `Run Keyword And Ignore Error`, and later fails in another keyword
- **THEN** the failure details list the calls of the later failure first, then a line `Caught: ` with the first line of the caught failure's message, followed by the calls of the caught failure

#### Scenario: Failure in the body and in the teardown

- **WHEN** a step of a test fails, and then its teardown fails as well
- **THEN** an empty line separates the failure details from the test's failure message, and they show two failures, each beginning with the first line of its message and listing its own calls

### Requirement: Navigating from a failed test

Navigating from a failed test whose failure details list failed keywords SHALL open the call in the test that led to its first failure that is not marked as caught. A failed test without failed keywords, for example one that failed in its suite setup or suite teardown, SHALL show its message only. A failed test without failed keywords other than caught ones SHALL navigate to its own line.

#### Scenario: Navigating from the failed test

- **WHEN** the user navigates to the source of `Third Test Fails` from the results tree
- **THEN** the editor opens `tests/sample.robot` at the line of the call of `Build Greeting`

#### Scenario: Navigating past a caught failure

- **WHEN** a test caught a failing `Should Be Equal` with `TRY`/`EXCEPT` and then failed in the keyword `Check Value`
- **THEN** navigating from the test opens its call of `Check Value`

#### Scenario: Failure in the suite setup

- **WHEN** a test fails because the suite setup of its suite failed
- **THEN** selecting the test shows only its failure message, and navigating from it opens the test's own line

## ADDED Requirements

### Requirement: A keyword that turns failures into its own is one failure in the failure details

When a keyword fails with an error of its own after failures inside it, as Wait Until Keyword Succeeds does after its last attempt or Run Keyword And Expect Error after another error, the failure details SHALL show it as one failure, with the calls of the last failure inside it, and no failures of their own for the failures inside it. A call on the same line as the call it ran in, as a keyword that a Run Keyword variant runs, SHALL not be listed again.

#### Scenario: Retried keyword

- **WHEN** the step `Wait Until Keyword Succeeds    3x    10ms    Should Be Equal    a    b` of a test fails
- **THEN** the failure details show one failure, with the line of the call of `Wait Until Keyword Succeeds`, and the test's failure message is `Keyword 'Should Be Equal' failed after retrying 3 times. The last error was: a != b`

#### Scenario: Keyword that collects failures

- **WHEN** a keyword under `robot:continue-on-failure` fails in `Should Be Equal    c    d` and `Should Be Equal    e    f`
- **THEN** the failure details show two failures, `c != d` and `e != f`, each with the call of the keyword and its own call of `Should Be Equal`
