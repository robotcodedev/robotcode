# Spec: repl-variable-listing

## Purpose

Defines what the `.vars` dot-command of `robotcode repl` and `robotcode robot-debug` lists — at the normal prompt and at a debugger stop — and how the `--user` option narrows the listing to the variables the user cares about.

## Requirements

### Requirement: Variable listing at the prompt and at a stop

`.vars` SHALL list every variable visible in the current scope with a truncated representation of its value. At a debugger stop it SHALL instead list the selected frame's variables grouped by scope (`Local`, `Test`, `Suite`, `Global`), each variable in the innermost scope that introduces it; a scope without variables SHALL print `(none)`.

#### Scenario: Listing at a debugger stop
- **WHEN** the run is stopped in a test after `${local}=    Set Variable    value` and `.vars` is entered
- **THEN** `${local}` is listed under the test-level scope and Robot Framework's built-in variables such as `${SUITE_NAME}` and `${OUTPUT_DIR}` are listed under `Suite` and `Global`

### Requirement: The user option hides built-in variables everywhere

`.vars --user` SHALL hide exactly the variables Robot Framework sets itself — `${TEMPDIR}`, `${EXECDIR}`, `&{OPTIONS}`, `${/}`, `${:}`, `${\n}`, `${SPACE}`, `${True}`, `${False}`, `${None}`, `${null}`, `${OUTPUT_DIR}`, `${OUTPUT_FILE}`, `${REPORT_FILE}`, `${LOG_FILE}`, `${DEBUG_FILE}`, `${LOG_LEVEL}`, `${PREV_TEST_NAME}`, `${PREV_TEST_STATUS}`, `${PREV_TEST_MESSAGE}`, `${SUITE_NAME}`, `${SUITE_SOURCE}`, `${SUITE_DOCUMENTATION}`, `&{SUITE_METADATA}`, `${SUITE_STATUS}`, `${SUITE_MESSAGE}`, `${TEST_NAME}`, `@{TEST_TAGS}`, `${TEST_DOCUMENTATION}`, `&{TEST_METADATA}`, `${TEST_STATUS}`, `${TEST_MESSAGE}`, `${KEYWORD_STATUS}` and `${KEYWORD_MESSAGE}` — and the REPL's own result variable `${_}`, with names compared the way Robot Framework compares variable names (ignoring case, spaces and underscores), both at the normal prompt and in every scope of the listing at a debugger stop. Every other variable SHALL be kept, including user variables whose names start like a built-in one (`${SUITE_VAR}`, `${TEST_USER}`, `${TESTDATA}`).

#### Scenario: User option at a debugger stop
- **WHEN** the run is stopped in a test with `${local}` assigned, the suite defines `${SUITE_VAR}`, and `.vars --user` is entered
- **THEN** the listing contains `${local}` and `${SUITE_VAR}`
- **AND** it contains neither `${TEST_NAME}`, `${SUITE_NAME}`, `${OUTPUT_DIR}` nor `&{OPTIONS}`

#### Scenario: Scope emptied by the filter
- **WHEN** the `Global` scope contains only built-in variables and `.vars --user` is entered at a stop
- **THEN** `Global:` is followed by `(none)`

#### Scenario: Constant built-ins at the normal prompt
- **WHEN** a REPL session assigns `${x}` and `.vars --user` is entered at the normal prompt
- **THEN** `${x}` is listed and `${/}`, `${True}`, `${None}` and `${SPACE}` are not

#### Scenario: Look-alike names are kept
- **WHEN** the test assigns `${TESTDATA}`, the suite defines `${SUITE_VAR}` and `.vars --user` is entered at a stop
- **THEN** `${TESTDATA}` and `${SUITE_VAR}` are listed

#### Scenario: Result variable is hidden
- **WHEN** a keyword has been run at the prompt or at a stop, so the REPL has set `${_}`, and `.vars --user` is entered
- **THEN** `${_}` is not listed, and `.vars` without the flag lists it
