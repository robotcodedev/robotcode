# Spec Delta

## MODIFIED Requirements

### Requirement: Stack trace at a failure stop

The answer to `exceptionInfo` at a failure stop SHALL carry a stack trace in its details: one line per element of the call stack, outermost first as Python lists calls, suites left out, with the element's name as the call stack shows it and the absolute path and line it is at. When Robot Framework logged a Python traceback with the failure the stop shows, the stack trace SHALL end with an empty line and that traceback as Robot Framework logs it, whatever the log level of the run.

#### Scenario: Calls that led to the failure

- **WHEN** a run stops at the failure of `Should Be Equal    1    2` in line 13 of `fail.robot`, in the user keyword `My Failing Keyword`, which the test `Failing Test` of the suite `Fail` calls in line 6
- **THEN** the stack trace has the line `Fail.Failing Test` with the absolute path of `fail.robot` and `:6`, then the line `My Failing Keyword` with the same path and `:13`, and no line for the suite `Fail`

#### Scenario: One keyword level up

- **WHEN** the run continues and stops again at `My Failing Keyword`
- **THEN** the stack trace has only the line `Fail.Failing Test` with the absolute path of `fail.robot` and `:6`

#### Scenario: Python traceback at the default log level

- **WHEN** the keyword `Fail In Python` of the library `MyLib` fails with `ValueError` in a run with the default log level INFO
- **THEN** the stack trace ends with an empty line and Robot Framework's traceback, which begins with `Traceback (most recent call last):` and names the file `MyLib.py` with the line that raised the error

#### Scenario: No traceback for a keyword of Robot Framework

- **WHEN** `Should Be Equal    1    2` fails
- **THEN** the stack trace has no traceback, since Robot Framework leaves its own code out of tracebacks and logs `None` as the traceback of this failure

#### Scenario: Failed test

- **WHEN** a run with the exception filter `failed_test` stops because the test `Failing Test` failed
- **THEN** the stack trace has only the line `Fail.Failing Test` with the absolute path of `fail.robot` and the line of the test's name

#### Scenario: Links in VS Code's exception widget

- **WHEN** VS Code shows the stop at the failure of `Should Be Equal    1    2` and the user follows the link `…/fail.robot:6` in the exception widget
- **THEN** the editor shows line 6 of `fail.robot`
