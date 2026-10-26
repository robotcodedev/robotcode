# Spec: debug-expressions

## Purpose

During a debug session, the editor asks the language server for the expression under the mouse, so that the debugger can show its value. The rules hold for the semantic-model analysis path, the default from `semantic-model-switchover` on.

## ADDED Requirements

### Requirement: Expression under the cursor

The evaluatable expression at a position SHALL consist of the range of the variable name, without `${`, `@{`, `&{` and the closing brace, and the variable as expression. There SHALL be a result only with the cursor on the name or on its closing brace; on `$`, `{`, after the closing brace, on keyword names, separators and plain text there SHALL be none.

#### Scenario: Cursor on a variable name
- **WHEN** the expression is requested with the cursor on `x` in `Log    ${x}` after an assignment of `${x}`
- **THEN** the result has the range of `x` and the expression `${x}`

#### Scenario: Cursor on a keyword name
- **WHEN** the expression is requested with the cursor on `Log` in `Log    ${x}`
- **THEN** there is no result

#### Scenario: Built-in variable
- **WHEN** the expression is requested with the cursor on `EMPTY` in `Log    ${EMPTY}`
- **THEN** the result has the expression `${EMPTY}`

### Requirement: Conditions

A `$var` reference in the condition of `IF`, `ELSE IF`, an inline `IF` or `WHILE` SHALL give the expression `${var}`.

#### Scenario: Condition of an IF
- **WHEN** the expression is requested with the cursor on `x` in `IF    $x == '1'` after an assignment of `${x}`
- **THEN** the result has the range of `x` and the expression `${x}`

### Requirement: Inline Python

In inline Python `${{ }}`, both `$var` and `${var}` references SHALL give the variable.

#### Scenario: Variable syntax inside inline Python
- **WHEN** the expression is requested with the cursor on `y` in `Log    ${{ $x + ${y} }}` after assignments of `${x}` and `${y}`
- **THEN** the result has the expression `${y}`

### Requirement: Variables after an empty variable

An empty variable `${}` SHALL NOT hide the variables after it in the same cell.

#### Scenario: Variable after an empty variable
- **WHEN** the expression is requested with the cursor on `x` in `Log    ${} ${x}` after an assignment of `${x}`
- **THEN** the result has the expression `${x}`

### Requirement: Definitions

Assignment targets, `VAR`, `FOR` and `EXCEPT AS` variables, names in the Variables section and embedded arguments of a keyword name SHALL give the variable. At a definition whose name contains a variable, that variable SHALL give a result as in an assignment, also when Robot Framework cannot resolve the name statically.

#### Scenario: Assignment target
- **WHEN** the expression is requested with the cursor on `later` in `${later}=    Set Variable    1`
- **THEN** the result has the expression `${later}`

#### Scenario: VAR with a nested name
- **WHEN** the expression is requested with the cursor on `x` in `VAR    ${${x}}    v` after an assignment of `${x}`, on Robot Framework 7.0 or newer
- **THEN** the result has the expression `${x}`

### Requirement: Typed variables

From Robot Framework 7.3 on, the type of a typed variable SHALL give no result. Outside `[Arguments]`, its name SHALL give the variable without the type.

#### Scenario: Typed assignment
- **WHEN** the expression is requested with the cursor on `t` and then on `int` in `${t: int}=    Set Variable    1`, on Robot Framework 7.3 or newer
- **THEN** `t` gives the expression `${t}` and `int` no result
