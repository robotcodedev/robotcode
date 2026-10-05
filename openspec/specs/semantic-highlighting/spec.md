# Spec: semantic-highlighting

## Purpose

Defines which semantic tokens the RobotCode language server sends for Robot Framework files, so that they add what the analysis knows on top of the TextMate grammar without painting over the syntax the grammar already shows.

## Requirements

### Requirement: Variables get a token for their name only

For every variable reference and every variable definition, the language server SHALL send exactly one semantic token per variable name, carrying the type and the modifiers the analysis computed for that variable. It SHALL NOT send tokens for:
- the prefix (`$`, `@`, `&`, `%`) and the braces;
- item-access brackets and literal item content;
- the `=` of an assignment;
- type-hint separators, default values of environment variables and embedded-argument patterns;
- inline Python expressions (`${{ }}`), neither for their delimiters nor for their content.

This SHALL hold at every site where Robot Framework defines or uses variables:
- declarations in `*** Variables ***`;
- keyword-call assignments, including several targets and item assignments such as `${DICT}[key]=`;
- `VAR`, `FOR` loop variables and `EXCEPT ... AS` targets;
- `[Arguments]` declarations;
- embedded arguments in keyword names, and embedded argument values in keyword calls;
- usages in arguments and settings, including nested variables, item access and environment variables.

#### Scenario: Declarations in the Variables section
- **WHEN** the line `${PAGE_OBJECT}    ${NONE}` in a `*** Variables ***` section is analyzed
- **THEN** the only tokens on the line are variable tokens for `PAGE_OBJECT` and `NONE`

#### Scenario: Variable inside an argument
- **WHEN** `Log    Hello ${name}!` is analyzed
- **THEN** `Log` gets a keyword-call token, `name` gets a variable token, and `Hello `, `${`, `}` and `!` get no token

#### Scenario: Item assignment
- **WHEN** `${DICT}[key]=    Set Variable    x` is analyzed
- **THEN** `DICT` gets a variable token, and `${`, `}`, `[key]` and `=` get no token

#### Scenario: Variable in an item access
- **WHEN** `Log    ${DICT}[${key}]` is analyzed
- **THEN** `DICT` and `key` get variable tokens and none of the braces and brackets does

#### Scenario: Nested variable
- **WHEN** `Log    ${NESTED_${SCALAR}}` is analyzed
- **THEN** `NESTED_` and `SCALAR` get variable tokens and none of the four braces does

#### Scenario: Environment variable with a default value
- **WHEN** `Log    %{MISSING=default}` is analyzed
- **THEN** `MISSING` gets a variable token, and `%{`, `=`, `default` and `}` get no token

#### Scenario: Inline Python expression
- **WHEN** `Log    ${{ len($LIST) }}` is analyzed
- **THEN** no token is sent for any part of `${{ len($LIST) }}`

#### Scenario: Embedded argument value in a keyword call
- **WHEN** the keyword `The result of ${a} is ${b}` exists and the call `The result of ${X} is 5` is analyzed
- **THEN** `X` gets a variable token with the embedded modifier, `5` gets an argument token with the embedded modifier, and `${` and `}` get no token

#### Scenario: Embedded argument in a keyword name
- **WHEN** the keyword name `Embedded ${n:\d+} Here` is analyzed
- **THEN** `n` gets a variable token, and `${`, `:`, `\d+` and `}` get no token

### Requirement: Variable names end where Robot Framework ends them

The language server SHALL determine the name of a variable as Robot Framework does at that position:
- A type hint SHALL be split off only with Robot Framework 7.3 or later, at the last `": "`, and only at these sites: declarations in `*** Variables ***`, keyword-call assignments, `VAR`, `FOR` loop variables, `[Arguments]` declarations and embedded arguments in keyword names. Everywhere else `: ` belongs to the name.
- An embedded-argument pattern SHALL be split off only in keyword names, also after a type hint as in `${count: int:\d+}`.
- The extended variable syntax SHALL be split off only where a variable is used, and only when neither a visible variable nor a number has the full name. Then the token covers the base name only. Names in definitions and keyword names are taken as they are.

A type hint that is split off SHALL get one `type` token, and its `: ` separator SHALL get none.

#### Scenario: Type hint in an assignment
- **WHEN** `${count: int}=    Get Count` is analyzed with Robot Framework 7.3 or later
- **THEN** `count` gets a variable token, `int` gets a type token, and `: ` gets no token

#### Scenario: Type hint before Robot Framework 7.3
- **WHEN** `${count: int}=    Get Count` is analyzed with Robot Framework 7.2
- **THEN** `count: int` gets one variable token

#### Scenario: Colons in a usage
- **WHEN** `${a}` is defined and `Log    ${a: int} ${a:x}` is analyzed with Robot Framework 7.3 or later
- **THEN** both get a variable token for `a` only, and neither `int` nor `x` gets a type token or any other token

#### Scenario: Type and pattern in a keyword name
- **WHEN** the keyword name `Typed ${count: int:\d+} Times` is analyzed with Robot Framework 7.3 or later
- **THEN** `count` gets a variable token, `int` gets a type token, and `\d+` gets no token

#### Scenario: Extended variable syntax
- **WHEN** `${OBJ}` is defined, no `${OBJ.attr}` is defined, and `Log    ${OBJ.attr}` is analyzed
- **THEN** `OBJ` gets a variable token and `.attr` gets no token

#### Scenario: Name that looks like extended syntax
- **WHEN** `${MY-VAR}` is defined in `*** Variables ***` and `Log    ${MY-VAR}` is analyzed
- **THEN** `MY-VAR` gets one variable token

### Requirement: Argument declarations are parameters

Each argument declared in `[Arguments]` SHALL get one `parameter` token over its name. This holds for `$`, `@` and `&` arguments, with or without a default value. The `=` and a literal default value SHALL get no token, and variables inside a default value SHALL get variable tokens.

#### Scenario: Arguments with and without default values
- **WHEN** `[Arguments]    ${a}    ${b}=default    ${c}=${DEFAULT}    @{rest}    &{named}` is analyzed
- **THEN** `a`, `b`, `c`, `rest` and `named` get parameter tokens, `DEFAULT` gets a variable token, and `=` and `default` get no token

### Requirement: Only variables get variable tokens

The language server SHALL send `variable` tokens only for variable names. An option of a control structure (`EXCEPT`, `WHILE`, `FOR` or `VAR`) SHALL get one control-flow token that covers `name=value`.

#### Scenario: WHILE options
- **WHEN** `WHILE    True    limit=3    on_limit=pass` is analyzed
- **THEN** `limit=3` and `on_limit=pass` get one control-flow token each

#### Scenario: EXCEPT option
- **WHEN** `EXCEPT    x    type=glob    AS    ${err}` is analyzed
- **THEN** `type=glob` gets one control-flow token and `err` gets a variable token
