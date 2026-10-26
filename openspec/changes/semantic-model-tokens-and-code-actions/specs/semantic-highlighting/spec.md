# Spec Delta

## MODIFIED Requirements

### Requirement: Only variables get variable tokens

The language server SHALL send `variable` tokens only for variable names. An option of a control structure (`EXCEPT`, `WHILE`, `FOR` or `VAR`) SHALL get control-flow tokens over `name=value`, except for the variables in its value: each of them SHALL get the tokens of a variable in an argument, one token for its name and none for its prefix and braces.

#### Scenario: WHILE options
- **WHEN** `WHILE    True    limit=3    on_limit=pass` is analyzed
- **THEN** `limit=3` and `on_limit=pass` get one control-flow token each

#### Scenario: EXCEPT option
- **WHEN** `EXCEPT    x    type=glob    AS    ${err}` is analyzed
- **THEN** `type=glob` gets one control-flow token and `err` gets a variable token

#### Scenario: Variable in an option value
- **WHEN** `${FIRST}` is defined and `FOR    ${i}    ${v}    IN ENUMERATE    @{LIST}    start=${FIRST}` is analyzed
- **THEN** `start=` gets a control-flow token and `FIRST` a variable token, and `${` and `}` get no token

#### Scenario: Text and a variable in an option value
- **WHEN** `${N}` is defined and `WHILE    True    limit=3    on_limit_message=Failed after ${N} rounds` is analyzed with Robot Framework 6.1 or later
- **THEN** `on_limit_message=Failed after ` and ` rounds` get control-flow tokens and `N` a variable token

### Requirement: Arguments of keyword calls

Plain argument text, inline Python `${{ }}` and `$var` references in expressions SHALL get no tokens; variables in arguments SHALL get `variable` tokens. In a call of a keyword with embedded arguments, the fixed text SHALL get `keywordCall` tokens, also right after a value, an embedded value an `argument` token with the `embedded` modifier and a variable as value a `variable` token with `embedded`, also where the argument has a custom pattern, which a variable matches as well.

#### Scenario: Expression argument
- **WHEN** a test contains `Should Be True    $X == 'x'`
- **THEN** only `Should Be True` gets a token

#### Scenario: Embedded value
- **WHEN** a keyword `Add ${n}` exists and a test contains `Add 5`
- **THEN** `Add ` gets a `keywordCall` token and `5` an `argument` token with the `embedded` modifier

#### Scenario: Variable for an embedded argument with a custom pattern
- **WHEN** a keyword `Count ${n:\d+} Items` exists, `${X}` is defined and a test contains `Count ${X} Items`
- **THEN** `Count ` and ` Items` get `keywordCall` tokens and `X` a `variable` token with the `embedded` modifier

#### Scenario: Fixed text right after a value
- **WHEN** a keyword `Px ${n}px` exists and a test contains `Px 5px`
- **THEN** `Px ` gets a `keywordCall` token, `5` an `argument` token with the `embedded` modifier and `px` a `keywordCall` token

### Requirement: BDD prefixes

A `Given`, `When`, `Then`, `And` or `But` prefix in any case, and a localized prefix (Robot Framework 6.0 and newer), SHALL get a `bddPrefix` token when Robot Framework calls the keyword without the prefix: from Robot Framework 7.1 on when the name without the prefix resolves, before 7.1 only when the full name does not; the rest is rendered like a keyword call. When the keyword does not resolve, the whole cell SHALL get one `keywordCall` token.

#### Scenario: Prefix of a resolved keyword
- **WHEN** a test contains `Given Log    x`
- **THEN** `Given` gets a `bddPrefix` token and `Log` a `keywordCall` token with the `builtin` modifier

#### Scenario: Prefix of a keyword that does not resolve
- **WHEN** a test contains `Given Unknown Keyword`
- **THEN** `Given Unknown Keyword` gets one `keywordCall` token

#### Scenario: Localized prefix
- **WHEN** a file with `Language: German` contains `Angenommen Log    x`, on Robot Framework 6.0 or newer
- **THEN** `Angenommen` gets a `bddPrefix` token and `Log` a `keywordCall` token

#### Scenario: Name that resolves with and without the prefix
- **WHEN** keywords `Prefixed` and `Given Prefixed` exist and a test calls `Given Prefixed`, on Robot Framework 7.1 or newer
- **THEN** `Given` gets a `bddPrefix` token and `Prefixed` a `keywordCall` token, as Robot Framework calls `Prefixed`

#### Scenario: Name that resolves with and without the prefix before Robot Framework 7.1
- **WHEN** keywords `Prefixed` and `Given Prefixed` exist and a test calls `Given Prefixed`, on Robot Framework 7.0 or older
- **THEN** `Given Prefixed` gets one `keywordCall` token, as Robot Framework calls `Given Prefixed`

### Requirement: Control structures

`FOR`, `END`, `IF`, `ELSE IF`, `ELSE`, `TRY`, `EXCEPT` with its `AS`, `FINALLY`, `WHILE`, `BREAK`, `CONTINUE`, `RETURN` and `GROUP` (Robot Framework 7.2 and newer) SHALL get `controlFlow` tokens, `IN`, `IN RANGE`, `IN ENUMERATE` and `IN ZIP` `forSeparator` tokens. Loop values, conditions, `EXCEPT` patterns and `GROUP` names SHALL get no tokens except variables. A word that Robot Framework rejects at its place, such as `END` outside a block, SHALL get an `error` token.

#### Scenario: FOR loop
- **WHEN** a test contains `FOR    ${i}    IN RANGE    3`
- **THEN** `FOR` gets a `controlFlow` token, `i` a `variable` token and `IN RANGE` a `forSeparator` token, and `3` gets none

#### Scenario: Condition
- **WHEN** an IF block contains `ELSE IF    ${x} == 2`
- **THEN** `ELSE IF` gets a `controlFlow` token and `x` a `variable` token

#### Scenario: END outside a block
- **WHEN** a test contains `END` without an open block
- **THEN** `END` gets an `error` token

#### Scenario: AS of EXCEPT
- **WHEN** a TRY block contains `EXCEPT    x    AS    ${e}`
- **THEN** `EXCEPT` and `AS` get `controlFlow` tokens and `e` a `variable` token, on every supported Robot Framework version
