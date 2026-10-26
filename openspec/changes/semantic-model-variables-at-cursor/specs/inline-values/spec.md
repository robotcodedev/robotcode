# Spec Delta

## MODIFIED Requirements

### Requirement: Lines that get inline values

Inline values SHALL be produced for the lines from the start of the requested range up to the line the debugger stopped at, for the whole of every statement that begins on that line, also the branches of an inline IF, and for the continuation lines of the stopped statement. The stopped location SHALL limit the lines, not the columns. Lines after the stopped statement SHALL never get values.

#### Scenario: Stop in the middle of a test
- **WHEN** a test contains `${x}=    Set Variable    1`, `${b}=    Set Variable    ${x}`, `Log    ${x} ${b}` and `Log    ${b}`, and inline values are requested for the whole test with the debugger stopped at `Log    ${x} ${b}`
- **THEN** the occurrences of `x` and `b` in the first three lines get values, and the last line gets none

#### Scenario: Inline IF on the stopped line
- **WHEN** `${a}`, `${b}` and `${c}` are assigned in earlier lines, and the debugger stopped at `IF    $c    Log    ${a}    ELSE    Log    ${b}` with the stopped location VS Code sends, an empty range at character 1 of that line
- **THEN** `c`, `a` and `b` get values

#### Scenario: Continuation line of the stopped statement
- **WHEN** `${a}` and `${b}` are assigned in earlier lines, and the debugger stopped at `Log Many    ${a}`, followed by the line `...    ${b}` and the line `Log    ${a}`
- **THEN** `a` and `b` of the stopped statement get values, and the line `Log    ${a}` after it gets none

### Requirement: Each occurrence is an evaluatable expression

Every occurrence that gets a value SHALL become an evaluatable expression whose range is the variable name without `${`, `@{`, `&{` and the closing brace, and whose expression is the variable as written in the code, without a type hint. With item access, or with attribute access that calls no method, the range SHALL reach from the name to the end of the access and the expression SHALL include the access; an access that calls a method SHALL give the base variable only.

#### Scenario: Scalar variable
- **WHEN** the debugger stopped at `Log    ${x}` after `${x}=    Set Variable    1`
- **THEN** the occurrence in `Log    ${x}` gets an evaluatable expression with the range of `x` and the expression `${x}`

#### Scenario: Spelling in the code
- **WHEN** the Variables section contains `${My Var}    1` and the debugger stopped at `Log    ${my_var}`
- **THEN** the occurrence gets the expression `${my_var}`

#### Scenario: Item access
- **WHEN** the Variables section contains `@{LIST}    a    b` and the debugger stopped at `Log    ${LIST}[0]`
- **THEN** the occurrence gets a range from `LIST` to the end of `[0]` and the expression `${LIST}[0]`

#### Scenario: Attribute access
- **WHEN** `${obj}` is assigned in an earlier line and the debugger stopped at `Log    ${obj.attr}`
- **THEN** the occurrence gets a range over `obj.attr` and the expression `${obj.attr}`

#### Scenario: Method call
- **WHEN** `${s}` is assigned in an earlier line and the debugger stopped at `Log    ${s.upper()}`
- **THEN** the occurrence gets the range of `s` and the expression `${s}`

### Requirement: Visibility at the stopped position

Variables SHALL be resolved at the stopped position: assignments in earlier lines, keyword arguments, also in their own `[Arguments]` line, embedded arguments, FOR and `EXCEPT AS` variables, `VAR` variables of every scope after their line in their test or keyword, the Variables section, imports, built-in and command-line variables, with local variables hiding suite variables. Unknown and escaped variables, `${CURDIR}`, number literals, variables assigned in later lines and the assignment target of the stopped line SHALL get no value.

#### Scenario: Assignment target of the stopped line
- **WHEN** the debugger stopped at `${b}=    Set Variable    ${x}` after `${x}=    Set Variable    1`
- **THEN** `x` in that line gets a value and `b` none

#### Scenario: Unknown variable
- **WHEN** the debugger stopped at `Log    ${unknown}`
- **THEN** `unknown` gets no value

#### Scenario: Argument in its own line
- **WHEN** a keyword declares `[Arguments]    ${p}` and the debugger stopped at `Log    ${p}` in that keyword
- **THEN** `p` gets a value in the `[Arguments]` line and in `Log    ${p}`

#### Scenario: VAR with suite scope
- **WHEN** the debugger stopped at `Log    ${y}` after `VAR    ${y}    2    scope=SUITE` in the same test, on Robot Framework 7.0 or newer
- **THEN** `y` gets a value in both lines

### Requirement: Conditions

A `$var` reference in the condition of `IF`, `ELSE IF`, an inline `IF` or `WHILE`, and in the arguments that BuiltIn keywords evaluate as Python expressions, such as the condition of `Should Be True`, SHALL get a value with the range of the name without `$` and the expression `${var}`.

#### Scenario: Condition of an IF
- **WHEN** the debugger stopped at `IF    $x == '1'` after `${x}=    Set Variable    1`
- **THEN** `x` gets an evaluatable expression `${x}`

#### Scenario: Condition of Should Be True
- **WHEN** the debugger stopped at `Should Be True    $x > 0` after `${x}=    Set Variable    1`
- **THEN** `x` gets an evaluatable expression `${x}`

#### Scenario: Further condition of Set Variable If
- **WHEN** the debugger stopped at `${r}=    Set Variable If    $x > 1    big    $y > 0    small    none` after assignments of `${x}` and `${y}`
- **THEN** `x` and `y` get evaluatable expressions `${x}` and `${y}`

### Requirement: Nested and dynamic names

The variables inside a nested variable name SHALL get values; the variable around them SHALL NOT get the value of a variable whose name is only the beginning of its name. At a definition whose name contains a variable, they SHALL get values as in an assignment, also when Robot Framework cannot resolve the name statically.

#### Scenario: VAR with a nested name
- **WHEN** the debugger stopped at `VAR    ${${x}}    value ${x}` after an assignment of `${x}`, on Robot Framework 7.0 or newer
- **THEN** both occurrences of `x` get values

#### Scenario: Name that begins like another variable
- **WHEN** the Variables section contains `${SUITE}    s` and `${x}    1`, and the debugger stopped at `Log    ${SUITE${x}}`
- **THEN** `x` gets a value, and no occurrence gets the expression `${SUITE}`

## ADDED Requirements

### Requirement: Only the variable of the stopped position

An occurrence SHALL get a value only when it resolves at its own position to the same variable as at the stopped position. Occurrences in another test or keyword, and occurrences before an assignment that hides a suite variable, SHALL get none, because their value at the stopped position belongs to another variable.

#### Scenario: Variable of another test
- **WHEN** tests `T` and `U` both assign `${x}`, and inline values are requested for both tests with the debugger stopped at `Log    ${x}` in `U`
- **THEN** the occurrences of `x` in `U` get values, and those in `T` get none

#### Scenario: Use before a local assignment
- **WHEN** the Variables section contains `${x}    suite`, and a test contains `Log    ${x}`, `${x}=    Set Variable    local` and `Log    ${x}`, with the debugger stopped at the last line
- **THEN** the first `Log    ${x}` gets no value, and the other two occurrences get values

### Requirement: Environment variables

An environment variable SHALL get a value with the range of its name and the expression of the whole variable with its default, such as `%{HOME=/tmp}`. Variables in its name or default SHALL get values of their own, with ranges that do not overlap it.

#### Scenario: Environment variable with a default
- **WHEN** the debugger stopped at `Log    %{HOME=/tmp}`
- **THEN** the occurrence gets the range of `HOME` and the expression `%{HOME=/tmp}`

#### Scenario: Variable in the default
- **WHEN** `${S}` is assigned in an earlier line and the debugger stopped at `Log    %{X=${S}}`
- **THEN** `X` gets the expression `%{X=${S}}` and `S` the expression `${S}`, each with the range of its name
