# debugger-exception-info Specification

## Purpose

Defines what the RobotCode debugger tells a debug client, such as VS Code or the IntelliJ plugin, about the failure a Robot Framework run is stopped at, so that the client can name what failed and show the failure message.

## Requirements

### Requirement: Exception information at a failure stop

The debugger SHALL advertise `supportsExceptionInfoRequest`. While a run is stopped at a failure by one of its exception filters, it SHALL answer `exceptionInfo` with the full name of the failed keyword as Robot Framework reports it, or the name of the failed test or suite, as the exception id; the failure message alone as the description; and the break mode `unhandled` for a stop of "Uncaught Failed Keywords" and `always` for the other filters.

#### Scenario: Library keyword

- **WHEN** a run with "Uncaught Failed Keywords" stops at the failure of `Should Be Equal    1    2`
- **THEN** `exceptionInfo` answers the exception id `BuiltIn.Should Be Equal`, the description `1 != 2` and the break mode `unhandled`

#### Scenario: One keyword level up

- **WHEN** the run continues and stops again at the user keyword `My Failing Keyword` of the suite file that called `Should Be Equal`
- **THEN** `exceptionInfo` answers the exception id `My Failing Keyword` and the description `1 != 2`

#### Scenario: Failure in a Python library

- **WHEN** a keyword `Fail In Python` of the library `MyLib` fails because its Python code raises `ValueError: invalid literal for int() with base 10: 'x'`
- **THEN** `exceptionInfo` answers the exception id `MyLib.Fail In Python` and the description `ValueError: invalid literal for int() with base 10: 'x'`, the message as Robot Framework reports it

#### Scenario: Failed test

- **WHEN** a run with the exception filter `failed_test` stops because the test `Login Works` failed with the message `Login failed`
- **THEN** `exceptionInfo` answers the exception id `Login Works`, the description `Login failed` and the break mode `always`

#### Scenario: VS Code's exception widget

- **WHEN** VS Code shows a run stopped at the failure of `Should Be Equal    1    2`
- **THEN** the exception widget below the line reads "Exception has occurred: BuiltIn.Should Be Equal" with `1 != 2` below it

### Requirement: Stack trace at a failure stop

The answer to `exceptionInfo` at a failure stop SHALL carry a stack trace in its details: one line per element of the call stack from the stop upward, suites left out, with the element's name as the call stack shows it and the absolute path and line it is at. When Robot Framework logged a Python traceback with the failure the stop shows, the stack trace SHALL end with an empty line and that traceback as Robot Framework logs it, whatever the log level of the run.

#### Scenario: Calls that led to the failure

- **WHEN** a run stops at the failure of `Should Be Equal    1    2` in line 13 of `fail.robot`, in the user keyword `My Failing Keyword`, which the test `Failing Test` of the suite `Fail` calls in line 6
- **THEN** the stack trace has the line `My Failing Keyword` with the absolute path of `fail.robot` and `:13`, then the line `Fail.Failing Test` with the same path and `:6`, and no line for the suite `Fail`

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

### Requirement: No exception information at other stops

When the run is stopped for another reason, at a breakpoint, after a step, at a pause or on entry, the debugger SHALL answer `exceptionInfo` with an error instead of information about an earlier failure.

#### Scenario: Stop at a breakpoint after a failure stop

- **WHEN** a run stopped at a keyword failure, continued, and now stops at a line breakpoint, and the client asks for `exceptionInfo`
- **THEN** the request fails with an error, and no information about the earlier failure is returned

### Requirement: The stop itself does not change

The stopped event at a failure SHALL keep its reason `exception`, its description, for example "Keyword failed.", and its text, for example "Keyword failed: 1 != 2", so that a client that does not ask for `exceptionInfo` shows what it showed before.

#### Scenario: IntelliJ plugin

- **WHEN** a debug run in PyCharm stops at the failure of `Should Be Equal    1    2`
- **THEN** the balloon reads "Keyword failed: 1 != 2", as before
