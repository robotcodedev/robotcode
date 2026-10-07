# Spec Delta

## MODIFIED Requirements

### Requirement: The user option hides built-in variables everywhere

`.vars --user` SHALL hide exactly the variables Robot Framework sets itself, which the requirements "Run variables hidden by the user option" and "Suite, test and keyword variables hidden by the user option" list, and the REPL's own result variable `${_}`, with names compared the way Robot Framework compares variable names (ignoring case, spaces and underscores), both at the normal prompt and in every scope of the listing at a debugger stop.

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

## ADDED Requirements

### Requirement: Other variables stay listed

With `.vars --user`, every other variable SHALL be kept, including user variables whose names start like a built-in one (`${SUITE_VAR}`, `${TEST_USER}`, `${TESTDATA}`).

#### Scenario: User variable named like a test variable
- **WHEN** the test assigns `${TEST_USER}` and `.vars --user` is entered at a stop
- **THEN** `${TEST_USER}` is listed

### Requirement: Run variables hidden by the user option

`.vars --user` SHALL hide these variables that Robot Framework sets itself: `${TEMPDIR}`, `${EXECDIR}`, `&{OPTIONS}`, `${/}`, `${:}`, `${\n}`, `${SPACE}`, `${True}`, `${False}`, `${None}`, `${null}`, `${OUTPUT_DIR}`, `${OUTPUT_FILE}`, `${REPORT_FILE}`, `${LOG_FILE}`, `${DEBUG_FILE}`, `${LOG_LEVEL}`, `${PREV_TEST_NAME}`, `${PREV_TEST_STATUS}` and `${PREV_TEST_MESSAGE}`.

#### Scenario: Run variables at the normal prompt
- **WHEN** `.vars --user` is entered at the normal prompt
- **THEN** neither `${TEMPDIR}` nor `${LOG_LEVEL}` is listed

### Requirement: Suite, test and keyword variables hidden by the user option

`.vars --user` SHALL hide these variables that Robot Framework sets itself for the current suite, test and keyword: `${SUITE_NAME}`, `${SUITE_SOURCE}`, `${SUITE_DOCUMENTATION}`, `&{SUITE_METADATA}`, `${SUITE_STATUS}`, `${SUITE_MESSAGE}`, `${TEST_NAME}`, `@{TEST_TAGS}`, `${TEST_DOCUMENTATION}`, `&{TEST_METADATA}`, `${TEST_STATUS}`, `${TEST_MESSAGE}`, `${KEYWORD_STATUS}` and `${KEYWORD_MESSAGE}`.

#### Scenario: Test variables at a debugger stop
- **WHEN** the run is stopped in a test and `.vars --user` is entered
- **THEN** neither `@{TEST_TAGS}` nor `${TEST_DOCUMENTATION}` is listed
