# Spec: selection-ranges

## Purpose

Selection ranges let the editor expand a selection step by step from a variable name over the cell and the statement to the enclosing blocks, the section and the file. The rules hold for the semantic-model analysis path, the default from `semantic-model-switchover` on.

## ADDED Requirements

### Requirement: Steps from the cell to the file

For a position, the selection ranges SHALL expand from the innermost step over the cell that contains the cursor, the statement, the enclosing blocks from inside to outside and the section to the file. A statement SHALL reach from column 0 to after the end of its line and cover all its continuation lines; a test or keyword SHALL reach up to the next definition or section.

#### Scenario: Argument in a test
- **WHEN** a file has a settings section and a test case section, and selection ranges are requested with the cursor inside `hello` in `    Log    hello` of test `T`
- **THEN** the steps are `hello`, the whole line, the test `T`, the test case section and the file

#### Scenario: Statement over two lines
- **WHEN** selection ranges are requested with the cursor inside `hello` in `    Log    hello`, followed by the line `    ...    WARN`
- **THEN** the step after the cell covers both lines

### Requirement: Variable step

With the cursor on the name of a variable or on its closing brace, the innermost step SHALL be the variable name without `${`, `@{`, `&{`, the closing brace and any item access, also for an unknown variable. In an item access, the step SHALL be the name of the accessed variable.

#### Scenario: Variable in an argument
- **WHEN** selection ranges are requested with the cursor on `name` in `Log    Hello ${name}!`
- **THEN** the steps start with `name` and `Hello ${name}!`

#### Scenario: Item access
- **WHEN** selection ranges are requested with the cursor on `DICT` in `Log    ${DICT}[k][0]`
- **THEN** the innermost step is `DICT`

#### Scenario: Unknown variable
- **WHEN** selection ranges are requested with the cursor on `UNDEFINED` in `Log    ${UNDEFINED}`
- **THEN** the innermost step is `UNDEFINED`

### Requirement: No variable step

Number literals such as `${42}`, escaped variables such as `\${x}` and comments SHALL get no variable step; the cell is then the innermost step.

#### Scenario: Number literal
- **WHEN** selection ranges are requested with the cursor on `42` in `Log    ${42}`
- **THEN** the innermost step is the cell `${42}`

### Requirement: Nested variables and inline Python

In a nested variable, the inner variable SHALL get a step. In inline Python `${{ }}`, both `$var` and `${var}` SHALL get a step for the variable name.

#### Scenario: Inner variable
- **WHEN** selection ranges are requested with the cursor on `b` in `Log    ${a_${b}}`
- **THEN** the innermost step is `b`

#### Scenario: Variable syntax inside inline Python
- **WHEN** selection ranges are requested with the cursor on `y` in `Log    ${{ $x + ${y} }}`
- **THEN** the innermost step is `y`

#### Scenario: Dollar syntax inside inline Python
- **WHEN** selection ranges are requested with the cursor on `x` in `Log    ${{ $x + ${y} }}`
- **THEN** the innermost step is `x`

### Requirement: Dynamic names at definitions

At a definition whose name contains a variable, in the Variables section, `VAR`, `FOR` and `EXCEPT AS`, the variables inside the name SHALL get steps as in an assignment, also when Robot Framework cannot resolve the name statically.

#### Scenario: VAR with a nested name
- **WHEN** selection ranges are requested with the cursor on `x` in `VAR    ${${x}}    v`, on Robot Framework 7.0 or newer
- **THEN** the innermost step is `x`

#### Scenario: Nested name in the Variables section
- **WHEN** the Variables section contains `${${X}}    value` and selection ranges are requested with the cursor on `X`
- **THEN** the innermost step is `X`

### Requirement: Typed variables

From Robot Framework 7.3 on, the name of a typed variable SHALL get a step. Outside `[Arguments]`, its type SHALL get none.

#### Scenario: Typed assignment
- **WHEN** selection ranges are requested with the cursor on `t` in `${t: int}=    Set Variable    1`, on Robot Framework 7.3 or newer
- **THEN** the innermost step is `t`
