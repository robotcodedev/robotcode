## ADDED Requirements

### Requirement: Conditions of the exception filters

When a debug client sets a condition on an exception filter, the debugger SHALL evaluate it each time a failure of that filter's kind occurs and SHALL stop for that filter only when the condition is true. A filter without a condition SHALL stop at every such failure. The condition SHALL be a Python expression in which Robot Framework variables are replaced, as for line breakpoints, and SHALL see the variables of the place where the failure ends.

#### Scenario: Condition that is false

- **WHEN** "Failed Tests" has the condition `1 == 2` and the tests `First` and `Second` fail
- **THEN** the run does not stop

#### Scenario: Condition on the test name

- **WHEN** "Failed Tests" has the condition `'${TEST_NAME}' == 'Second'` and the tests `First` and `Second` fail
- **THEN** the run stops once, at the end of `Second`

#### Scenario: Condition on the failure message of a test

- **WHEN** "Failed Tests" has the condition `'3 != 4' in $TEST_MESSAGE`, `First` fails with `1 != 2` and `Second` with `3 != 4`
- **THEN** the run stops once, at the end of `Second`

#### Scenario: Condition on a keyword filter

- **WHEN** "Failed Keywords" has the condition `'${TEST_NAME}' == 'Second'` and a keyword fails in each of the tests `First` and `Second`
- **THEN** the run stops only at the keyword that fails in `Second`

#### Scenario: Filter without a condition

- **WHEN** "Failed Tests" has no condition and the tests `First` and `Second` fail
- **THEN** the run stops at the end of each of them

#### Scenario: Edit Condition in VS Code

- **WHEN** the user sets the condition `'${TEST_NAME}' == 'Second'` on "Failed Tests" with **Edit Condition** in VS Code's Breakpoints view and debugs a suite whose tests `First` and `Second` fail
- **THEN** the run stops only at the end of `Second`

### Requirement: Variables of the failure in a condition

While the condition of an exception filter is evaluated, the debugger SHALL provide `${EXCEPTION_NAME}`, the name of the keyword, test or suite that failed, and `${EXCEPTION_MESSAGE}`, its failure message. The run SHALL NOT see these two variables, and a variable of the run with the same name SHALL keep its value.

#### Scenario: Name of the failed keyword

- **WHEN** "Failed Keywords" has the condition `$EXCEPTION_NAME == 'BuiltIn.Should Be Equal'`, the test `First` fails at `Should Be Equal` and the test `Second` at `Fail`
- **THEN** the run stops only at `Should Be Equal` in `First`

#### Scenario: Failure message with quotes

- **WHEN** "Failed Tests" has the condition `$EXCEPTION_MESSAGE == "Wrong 'value'"`, the test `First` fails with `Fail    Wrong 'value'` and the test `Second` with `Fail    Other`
- **THEN** the run stops only at the end of `First`

#### Scenario: The run doesn't see the variables

- **WHEN** a condition on "Failed Keywords" is evaluated at a failure in a test whose teardown runs `Variable Should Not Exist    ${EXCEPTION_NAME}`
- **THEN** the teardown passes

#### Scenario: A variable of the run with the same name

- **WHEN** a test sets `${EXCEPTION_MESSAGE}` to `mine` and then fails with `Fail    boom`, "Failed Keywords" has the condition `$EXCEPTION_MESSAGE == 'boom'`, and the test's teardown checks `${EXCEPTION_MESSAGE}`
- **THEN** the run stops at `Fail`, and the teardown finds `mine`

### Requirement: A condition that cannot be evaluated

When the condition of an exception filter cannot be evaluated, the debugger SHALL NOT stop for that filter and SHALL write the error to the debug console, naming the filter.

#### Scenario: Unknown variable

- **WHEN** "Failed Tests" has the condition `${nonexistent} == 1` and a test fails
- **THEN** the run does not stop, and the debug console shows `Exception breakpoint condition error (Failed Tests): Variable '${nonexistent}' not found.`

### Requirement: Switched exception filters stay switched

The debugger SHALL advertise that each exception filter takes a condition without giving a placeholder text for it, so that VS Code keeps recognizing the filters as the user has switched them on or off.

#### Scenario: A filter switched on before the update

- **WHEN** the user switched "Failed Tests" on in VS Code's Breakpoints view with the debugger before this change and debugs again after it
- **THEN** "Failed Tests" is still switched on

#### Scenario: Placeholder of the condition box

- **WHEN** the user chooses **Edit Condition** on an exception filter in VS Code's Breakpoints view
- **THEN** the box shows VS Code's own placeholder text
