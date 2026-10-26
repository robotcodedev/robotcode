# Spec: inline-values

## Purpose

When the debugger stops, inline values show the values of the variables in the lines up to the stopped line. The rules hold for the semantic-model analysis path, the default from `semantic-model-switchover` on.

## ADDED Requirements

### Requirement: Lines that get inline values

Inline values SHALL be produced for the lines from the start of the requested range up to the line the debugger stopped at. Lines after the stopped line SHALL never get values.

#### Scenario: Stop in the middle of a test
- **WHEN** a test contains `${x}=    Set Variable    1`, `${b}=    Set Variable    ${x}`, `Log    ${x} ${b}` and `Log    ${b}`, and inline values are requested for the whole test with the debugger stopped at `Log    ${x} ${b}`
- **THEN** the occurrences of `x` and `b` in the first three lines get values, and the last line gets none

### Requirement: Each occurrence is an evaluatable expression

Every occurrence of a variable that is visible at the stopped position SHALL become an evaluatable expression whose range is the variable name without `${`, `@{`, `&{` and the closing brace, and whose expression is the variable.

#### Scenario: Scalar variable
- **WHEN** the debugger stopped at `Log    ${x}` after `${x}=    Set Variable    1`
- **THEN** the occurrence in `Log    ${x}` gets an evaluatable expression with the range of `x` and the expression `${x}`

### Requirement: Visibility at the stopped position

Variables SHALL be resolved at the stopped position: assignments in earlier lines, keyword arguments, embedded arguments, FOR and `EXCEPT AS` variables, local `VAR` variables, the Variables section, imports, built-in and command-line variables, with local variables hiding suite variables. Unknown and escaped variables, `${CURDIR}`, number literals, variables assigned in later lines and the assignment target of the stopped line SHALL get no value.

#### Scenario: Assignment target of the stopped line
- **WHEN** the debugger stopped at `${b}=    Set Variable    ${x}` after `${x}=    Set Variable    1`
- **THEN** `x` in that line gets a value and `b` none

#### Scenario: Unknown variable
- **WHEN** the debugger stopped at `Log    ${unknown}`
- **THEN** `unknown` gets no value

### Requirement: Conditions

A `$var` reference in the condition of `IF`, `ELSE IF`, an inline `IF` or `WHILE` SHALL get a value with the range of the name without `$` and the expression `${var}`.

#### Scenario: Condition of an IF
- **WHEN** the debugger stopped at `IF    $x == '1'` after `${x}=    Set Variable    1`
- **THEN** `x` gets an evaluatable expression `${x}`

### Requirement: Inline Python

In inline Python `${{ }}`, both `$var` and `${var}` references SHALL get values.

#### Scenario: Both syntaxes in one expression
- **WHEN** the debugger stopped at `Log    ${{ $x + ${y} }}` after assignments of `${x}` and `${y}`
- **THEN** `x` and `y` both get values

### Requirement: Variables after an empty variable

An empty variable `${}` SHALL NOT end the scan of its cell; the variables after it SHALL get values.

#### Scenario: Variable after an empty variable
- **WHEN** the debugger stopped at `Log    ${} ${x}` after an assignment of `${x}`
- **THEN** `x` gets a value

### Requirement: Nested and dynamic names

The variables inside a nested variable name SHALL get values. At a definition whose name contains a variable, they SHALL get values as in an assignment, also when Robot Framework cannot resolve the name statically.

#### Scenario: VAR with a nested name
- **WHEN** the debugger stopped at `VAR    ${${x}}    value ${x}` after an assignment of `${x}`, on Robot Framework 7.0 or newer
- **THEN** both occurrences of `x` get values

### Requirement: Typed variables

From Robot Framework 7.3 on, a typed variable SHALL get its value under its name without the type.

#### Scenario: Typed assignment
- **WHEN** the debugger stopped at `Log    ${t}` after `${t: int}=    Set Variable    1`, on Robot Framework 7.3 or newer
- **THEN** `t` in the assignment gets an evaluatable expression `${t}`
