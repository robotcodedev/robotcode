# Spec Delta

## Purpose

Defines what the `.vars` dot-command of `robotcode repl` and `robotcode robot-debug` lists — at the normal prompt and at a debugger stop — and how the `--user` option narrows the listing to the variables the user cares about.

## ADDED Requirements

### Requirement: Variable listing at the prompt and at a stop

`.vars` SHALL list every variable visible in the current scope with a truncated representation of its value. At a debugger stop it SHALL instead list the selected frame's variables grouped by scope (`Local`, `Test`, `Suite`, `Global`), each variable in the innermost scope that introduces it; a scope without variables SHALL print `(none)`.

#### Scenario: Listing at a debugger stop
- **WHEN** the run is stopped in a test after `${local}=    Set Variable    value` and `.vars` is entered
- **THEN** `${local}` is listed under the test-level scope and Robot Framework's built-in variables such as `${SUITE_NAME}` and `${OUTPUT_DIR}` are listed under `Suite` and `Global`

### Requirement: The user option hides built-in variables everywhere

`.vars --user` SHALL hide Robot Framework's built-in variables — those named exactly like, or starting with, one of Robot Framework's reserved prefixes followed by `_` or a space (`SUITE`, `TEST`, `TASK`, `PREV`, `OUTPUT`, `LOG`, `REPORT`, `DEBUG_FILE`, `EXECDIR`, `TEMPDIR`, `CURDIR`, `OPTIONS`, `KEYWORD`, `SPACE`, …), and the constant built-ins `${/}`, `${:}`, `${\n}`, `${True}`, `${False}`, `${None}` and `${null}` — both at the normal prompt and in every scope of the listing at a debugger stop. Variables that merely start with a reserved word without the separator (`${TESTDATA}`) and the REPL's own result variable `${_}` SHALL be kept.

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
- **WHEN** the test assigns `${TESTDATA}` and `.vars --user` is entered at a stop
- **THEN** `${TESTDATA}` is listed
