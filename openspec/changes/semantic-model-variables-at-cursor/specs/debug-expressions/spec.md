# Spec Delta

## MODIFIED Requirements

### Requirement: Expression under the cursor

The evaluatable expression at a position SHALL consist of the range of the variable name, without `${`, `@{`, `&{` and the closing brace, and the variable as written there, without a type hint, as expression, whether or not the analysis can resolve it; the debugger evaluates it at run time. There SHALL be a result only with the cursor on the name or on its closing brace; on `$`, `{`, after the closing brace, on keyword names, separators, plain text and number literals there SHALL be none.

#### Scenario: Cursor on a variable name
- **WHEN** the expression is requested with the cursor on `x` in `Log    ${x}` after an assignment of `${x}`
- **THEN** the result has the range of `x` and the expression `${x}`

#### Scenario: Cursor on a keyword name
- **WHEN** the expression is requested with the cursor on `Log` in `Log    ${x}`
- **THEN** there is no result

#### Scenario: Built-in variable
- **WHEN** the expression is requested with the cursor on `EMPTY` in `Log    ${EMPTY}`
- **THEN** the result has the expression `${EMPTY}`

#### Scenario: Spelling in the code
- **WHEN** the Variables section contains `${My Var}    1` and the expression is requested with the cursor on `my_var` in `Log    ${my_var}`
- **THEN** the result has the expression `${my_var}`

#### Scenario: Variable set by a keyword
- **WHEN** a test contains `Set Test Variable    ${later}    1` and then `Log    ${later}`, and the expression is requested with the cursor on `later` in `Log    ${later}`
- **THEN** the result has the expression `${later}`

#### Scenario: Use before the assignment
- **WHEN** a test contains `Log    ${x}` and then `${x}=    Set Variable    1`, and the expression is requested with the cursor on `x` in `Log    ${x}`
- **THEN** the result has the expression `${x}`

#### Scenario: Number literal
- **WHEN** the expression is requested with the cursor on `42` in `Log    ${42}`
- **THEN** there is no result

### Requirement: Conditions

A `$var` reference in the condition of `IF`, `ELSE IF`, an inline `IF` or `WHILE`, and in the arguments that BuiltIn keywords evaluate as Python expressions, such as the condition of `Should Be True`, SHALL give the expression `${var}`.

#### Scenario: Condition of an IF
- **WHEN** the expression is requested with the cursor on `x` in `IF    $x == '1'` after an assignment of `${x}`
- **THEN** the result has the range of `x` and the expression `${x}`

#### Scenario: Condition of Should Be True
- **WHEN** the expression is requested with the cursor on `x` in `Should Be True    $x > 0` after an assignment of `${x}`
- **THEN** the result has the range of `x` and the expression `${x}`

### Requirement: Definitions

Assignment targets, `VAR`, `FOR` and `EXCEPT AS` variables, `[Arguments]` names, names in the Variables section and embedded arguments of a keyword name SHALL give the variable. At a definition whose name contains a variable, that variable SHALL give a result as in an assignment, also when Robot Framework cannot resolve the name statically.

#### Scenario: Assignment target
- **WHEN** the expression is requested with the cursor on `later` in `${later}=    Set Variable    1`
- **THEN** the result has the expression `${later}`

#### Scenario: VAR with a nested name
- **WHEN** the expression is requested with the cursor on `x` in `VAR    ${${x}}    v` after an assignment of `${x}`, on Robot Framework 7.0 or newer
- **THEN** the result has the expression `${x}`

#### Scenario: Argument
- **WHEN** a keyword declares `[Arguments]    ${p}    ${q}=1` and the expression is requested with the cursor on `p` and then on `q`
- **THEN** `p` gives the expression `${p}` and `q` the expression `${q}`

### Requirement: Typed variables

From Robot Framework 7.3 on, the type of a typed variable SHALL give no result, and its name SHALL give the variable without the type, in `[Arguments]` as in the other definitions.

#### Scenario: Typed assignment
- **WHEN** the expression is requested with the cursor on `t` and then on `int` in `${t: int}=    Set Variable    1`, on Robot Framework 7.3 or newer
- **THEN** `t` gives the expression `${t}` and `int` no result

#### Scenario: Typed argument
- **WHEN** a keyword declares `[Arguments]    ${p: int}` and the expression is requested with the cursor on `p` and then on `int`, on Robot Framework 7.3 or newer
- **THEN** `p` gives the expression `${p}` and `int` no result

## ADDED Requirements

### Requirement: Item and attribute access

For a variable with item access, or with attribute access that calls no method, the range SHALL reach from the name to the end of the access, the expression SHALL include the access, and the cursor anywhere in that range SHALL give this result. An attribute access that calls a method SHALL give the base variable only, with the cursor on its name.

#### Scenario: Cursor on an index
- **WHEN** the expression is requested with the cursor on `0` in `Log    ${LIST}[0]`
- **THEN** the result has a range from `LIST` to the end of `[0]` and the expression `${LIST}[0]`

#### Scenario: Cursor on the name of an item access
- **WHEN** the expression is requested with the cursor on `LIST` in `Log    ${LIST}[0][1]`
- **THEN** the result has the expression `${LIST}[0][1]`

#### Scenario: Method call
- **WHEN** the expression is requested with the cursor on `s` and then on `upper` in `Log    ${s.upper()}`
- **THEN** `s` gives the range of `s` and the expression `${s}`, and `upper` gives no result

### Requirement: Environment variables

An environment variable SHALL give the range of its name and the expression of the whole variable with its default, such as `%{HOME=/tmp}`. Variables in its name or default SHALL give results of their own.

#### Scenario: Environment variable with a default
- **WHEN** the expression is requested with the cursor on `HOME` in `Log    %{HOME=/tmp}`
- **THEN** the result has the range of `HOME` and the expression `%{HOME=/tmp}`

#### Scenario: Variable in the default
- **WHEN** the expression is requested with the cursor on `S` in `Log    %{X=${S}}` after an assignment of `${S}`
- **THEN** the result has the range of `S` and the expression `${S}`

### Requirement: Nested names

With the cursor on the outer part of a nested variable, the result SHALL have the range of the outer name and the whole variable as written as expression, never a variable whose name is only the beginning of that name.

#### Scenario: Name that begins like another variable
- **WHEN** the Variables section contains `${SUITE}    s`, and the expression is requested with the cursor on `SUITE` in `Log    ${SUITE${x}}`
- **THEN** the result has the range of `SUITE${x}` and the expression `${SUITE${x}}`
