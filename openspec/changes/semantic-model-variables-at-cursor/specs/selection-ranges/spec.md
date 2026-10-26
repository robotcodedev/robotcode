# Spec Delta

## MODIFIED Requirements

### Requirement: Steps from the cell to the file

For a position, the selection ranges SHALL expand from the innermost step over the cell that contains the cursor, the statement, the enclosing blocks from inside to outside and the section to the file. A statement SHALL reach from column 0 to after the end of its line and cover all its continuation lines; a test or keyword SHALL reach up to the next definition or section. Two steps with the same range SHALL appear once.

#### Scenario: Argument in a test
- **WHEN** a file has a settings section and a test case section, and selection ranges are requested with the cursor inside `hello` in `    Log    hello` of test `T`
- **THEN** the steps are `hello`, the whole line, the test `T`, the test case section and the file

#### Scenario: Statement over two lines
- **WHEN** selection ranges are requested with the cursor inside `hello` in `    Log    hello`, followed by the line `    ...    WARN`
- **THEN** the step after the cell covers both lines

#### Scenario: File with one section
- **WHEN** a file consists of a test case section only, and selection ranges are requested with the cursor inside `hello` in `    Log    hello` of test `T`
- **THEN** the steps are `hello`, the whole line, the test `T` and the file, and no step repeats the range of the step before it

### Requirement: Variable step

With the cursor on the name of a variable or on its closing brace, the innermost step SHALL be the variable name without `${`, `@{`, `&{`, the closing brace and any item access, also for an unknown variable. In an item access, the step SHALL be the name of the accessed variable. The steps SHALL depend only on the text, not on which variables are defined: with extended variable syntax such as `${obj.attr}`, the name is the whole text between the braces, and the base `obj` is a step inside it.

#### Scenario: Variable in an argument
- **WHEN** selection ranges are requested with the cursor on `name` in `Log    Hello ${name}!`
- **THEN** the steps start with `name`, `${name}` and `Hello ${name}!`

#### Scenario: Item access
- **WHEN** selection ranges are requested with the cursor on `DICT` in `Log    ${DICT}[k][0]`
- **THEN** the innermost step is `DICT`

#### Scenario: Unknown variable
- **WHEN** selection ranges are requested with the cursor on `UNDEFINED` in `Log    ${UNDEFINED}`
- **THEN** the innermost step is `UNDEFINED`

#### Scenario: Extension of extended syntax
- **WHEN** selection ranges are requested with the cursor on `attr` in `Log    ${obj.attr}`, once with `${obj}` assigned in an earlier line and once without
- **THEN** both times the steps start with `obj.attr` and `${obj.attr}`

#### Scenario: Base of extended syntax
- **WHEN** selection ranges are requested with the cursor on `obj` in `Log    ${obj.attr}`
- **THEN** the steps start with `obj`, `obj.attr` and `${obj.attr}`

### Requirement: Typed variables

From Robot Framework 7.3 on, the name of a typed variable SHALL get a step and its type none. With the cursor on the type, the variable with its braces SHALL be the innermost step, in `[Arguments]` as in the other definitions.

#### Scenario: Typed assignment
- **WHEN** selection ranges are requested with the cursor on `t` in `${t: int}=    Set Variable    1`, on Robot Framework 7.3 or newer
- **THEN** the innermost step is `t`

#### Scenario: Type of an argument
- **WHEN** a keyword declares `[Arguments]    ${p: int}` and selection ranges are requested with the cursor on `int`, on Robot Framework 7.3 or newer
- **THEN** the innermost step is `${p: int}`

## ADDED Requirements

### Requirement: Steps around a variable name

After the name, the selection ranges SHALL have a step for the variable with its prefix and braces, one for the variable with its item access, and the steps of each variable that contains it. With the cursor in a literal item, the variable with its item access SHALL be the innermost step.

#### Scenario: Steps of an item access
- **WHEN** selection ranges are requested with the cursor on `DICT` in `Log    ${DICT}[k][0]`
- **THEN** the steps start with `DICT`, `${DICT}`, `${DICT}[k][0]` and the whole line

#### Scenario: Cursor in an item
- **WHEN** selection ranges are requested with the cursor on `k` in `Log    ${DICT}[k][0]`
- **THEN** the innermost step is `${DICT}[k][0]`

#### Scenario: Variable in an index
- **WHEN** selection ranges are requested with the cursor on `key` in `Log    ${DICT}[${key}]`
- **THEN** the steps start with `key`, `${key}` and `${DICT}[${key}]`

#### Scenario: Nested variable
- **WHEN** selection ranges are requested with the cursor on `b` in `Log    ${a_${b}}`
- **THEN** the steps start with `b`, `${b}`, `a_${b}` and `${a_${b}}`

### Requirement: Environment variables

An environment variable SHALL get the step of its name and then the whole variable with its default. Variables in its name or default SHALL get their own steps inside it.

#### Scenario: Environment variable with a default
- **WHEN** selection ranges are requested with the cursor on `HOME` in `Log    %{HOME=/tmp}`
- **THEN** the steps start with `HOME` and `%{HOME=/tmp}`

#### Scenario: Variable in the default
- **WHEN** selection ranges are requested with the cursor on `S` in `Log    %{X=${S}}`
- **THEN** the steps start with `S`, `${S}` and `%{X=${S}}`

### Requirement: $var references

A `$var` reference SHALL get the steps `var` and `$var` in the condition of `IF`, `ELSE IF`, an inline `IF` and `WHILE`, in the arguments that BuiltIn keywords evaluate as Python expressions, such as the condition of `Should Be True`, and in inline Python `${{ }}`.

#### Scenario: Condition of an IF
- **WHEN** selection ranges are requested with the cursor on `x` in `IF    $x > 1`
- **THEN** the steps start with `x` and `$x`

#### Scenario: Condition of Should Be True
- **WHEN** selection ranges are requested with the cursor on `x` in `Should Be True    $x > 1`
- **THEN** the steps start with `x` and `$x`

#### Scenario: Condition after ELSE IF
- **WHEN** selection ranges are requested with the cursor on `b` in `Run Keyword If    $a    Log    x    ELSE IF    $b    Log    y`
- **THEN** the steps start with `b` and `$b`

### Requirement: Variables after an empty variable

An empty variable `${}` SHALL NOT hide the variables after it in the same cell.

#### Scenario: Variable after an empty variable
- **WHEN** selection ranges are requested with the cursor on `x` in `Log    ${} ${x}`
- **THEN** the innermost step is `x`

### Requirement: Steps inside a cell

Between the innermost variable step and the cell, the selection ranges SHALL have a step for the keyword name without its BDD and import prefixes, then one with the import prefix, a step for the name and one for the value of a named argument, and a step for each embedded argument value in a keyword call.

#### Scenario: Keyword with prefixes
- **WHEN** selection ranges are requested with the cursor on `Log` in `Given BuiltIn.Log    x`
- **THEN** the steps start with `Log`, `BuiltIn.Log`, `Given BuiltIn.Log` and the whole line

#### Scenario: Value of a named argument
- **WHEN** selection ranges are requested with the cursor on `WARN` in `Log    hello    level=WARN`
- **THEN** the steps start with `WARN`, `level=WARN` and the whole line

#### Scenario: Embedded argument value
- **WHEN** a keyword `Add ${n}` exists and selection ranges are requested with the cursor on `5` in `Add 5`
- **THEN** the steps start with `5`, `Add 5` and the whole line

### Requirement: The cell at a boundary

With the cursor between a cell and the separator or line end after it, that cell SHALL be the cell of the position.

#### Scenario: Cursor at the end of a keyword name
- **WHEN** selection ranges are requested with the cursor directly after `Log` in `    Log    hello`
- **THEN** the innermost step is `Log`

#### Scenario: Cursor at the end of the line
- **WHEN** selection ranges are requested with the cursor directly after `${x}` at the end of `    Log    ${x}`
- **THEN** the innermost step is `${x}`

### Requirement: Branches of IF and TRY

Each branch of an IF or TRY block, from its header to the end of its body, SHALL be a step of its own between the statement and the whole block. A branch step SHALL NOT contain the branches after it.

#### Scenario: ELSE IF branch
- **WHEN** a test contains an IF block with an `ELSE IF` and an `ELSE` branch, and selection ranges are requested with the cursor in the body of the `ELSE IF` branch
- **THEN** after the statement come the `ELSE IF` branch without the `ELSE` branch, and then the whole IF block

#### Scenario: EXCEPT branch
- **WHEN** a test contains a TRY block with an `EXCEPT` and a `FINALLY` branch, and selection ranges are requested with the cursor in the body of the `EXCEPT` branch
- **THEN** after the statement come the `EXCEPT` branch without the `FINALLY` branch, and then the whole TRY block
