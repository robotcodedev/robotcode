# Spec Delta

## ADDED Requirements

### Requirement: Section headers get one token

A section header SHALL get one token over the whole cell: `headerSettings`, `headerVariable`, `headerTestcase`, `headerTask`, `headerKeyword` or `headerComment`, also for singular and localized headers (Robot Framework 6.0 and newer). An invalid section header SHALL get one `error` token before Robot Framework 6.1 and one `header` token from 6.1 on.

#### Scenario: Test case header
- **WHEN** `*** Test Cases ***` is analyzed
- **THEN** it gets one `headerTestcase` token

#### Scenario: Localized task header
- **WHEN** a file with `Language: German` contains `*** Aufgaben ***`, on Robot Framework 6.0 or newer
- **THEN** `*** Aufgaben ***` gets one `headerTask` token

#### Scenario: Invalid section header
- **WHEN** `*** Something ***` is analyzed on Robot Framework 6.1 or newer
- **THEN** it gets one `header` token

### Requirement: Comment sections and the language line

Lines in a comment section and text before the first section SHALL get no tokens, except a `Language:` line, which SHALL get one `config` token (Robot Framework 6.0 and newer). From Robot Framework 6.1 on, every data cell of an invalid section SHALL get a `comment` token.

#### Scenario: Language line
- **WHEN** a file starts with `Language: German`, on Robot Framework 6.0 or newer
- **THEN** that line gets one `config` token

#### Scenario: Comment section
- **WHEN** a `*** Comments ***` section contains `Log    x`
- **THEN** that line gets no tokens

#### Scenario: Content of an invalid section
- **WHEN** `*** Something ***` is followed by `here    there`, on Robot Framework 6.1 or newer
- **THEN** `here` and `there` get `comment` tokens

### Requirement: Setting names get a setting token

The name of a setting other than documentation and metadata SHALL get one `setting` token, in the settings section (also aliases such as `Task Setup` and localized names) and in brackets, where `[` and `]` get `operator` tokens; `[Return]` is a bracket setting too. A setting that Robot Framework rejects SHALL get one `error` token over its name cell and no tokens for the rest of its line. The values of tag, timeout and `Name` settings SHALL get no tokens except variables.

#### Scenario: Bracket setting with values
- **WHEN** a test contains `[Tags]    smoke    ${X}`
- **THEN** `[` gets an `operator` token, `Tags` a `setting` token, `]` an `operator` token and `X` a `variable` token, and `smoke` gets no token

#### Scenario: Setting in the settings section
- **WHEN** the settings section contains `Test Tags    t1`
- **THEN** `Test Tags` gets one `setting` token and `t1` none

#### Scenario: Rejected setting
- **WHEN** a test contains `[Unknown]    x`
- **THEN** the cell `[Unknown]` gets one `error` token and `x` none

### Requirement: Imports

`Library`, `Resource` and `Variables`, also localized, SHALL get `settingImport` tokens. The imported name SHALL get `namespace` tokens for its text and `variable` tokens for variables in it. `WITH NAME` and `AS` (Robot Framework 6.0 and newer) SHALL get `settingImport` tokens and the alias a `namespace` token. Other import arguments SHALL get no tokens except variables, and in a `Library` import the named arguments of the library's `__init__`.

#### Scenario: Library with an alias
- **WHEN** `Library    String    AS    S` is analyzed on Robot Framework 6.0 or newer
- **THEN** `Library` gets a `settingImport` token, `String` a `namespace` token, `AS` a `settingImport` token and `S` a `namespace` token

#### Scenario: Variable in an import name
- **WHEN** `Resource    ${CURDIR}/res.resource` is analyzed
- **THEN** `Resource` gets a `settingImport` token, `CURDIR` a `variable` token and `/res.resource` a `namespace` token

#### Scenario: Named argument of a library
- **WHEN** `Library    ./mylib.py    arg1    named=value` is analyzed and `named` is an argument of the library's `__init__`
- **THEN** `named` gets a `namedArgument` token and `=` an `operator` token, and `arg1` and `value` get none

### Requirement: Keywords in settings

The keyword of a setup or teardown setting SHALL be rendered like a keyword call, and `NONE` SHALL get one `argument` token. A resolved keyword of `Test Template` or `[Template]` SHALL be rendered like a keyword call; a template name that does not resolve and `NONE` SHALL get one `argument` token over the cell.

#### Scenario: Setup
- **WHEN** a test contains `[Setup]    Log    x`
- **THEN** `Log` gets a `keywordCall` token with the `builtin` modifier

#### Scenario: NONE as teardown
- **WHEN** a test contains `[Teardown]    NONE`
- **THEN** `NONE` gets one `argument` token

#### Scenario: Template that does not resolve
- **WHEN** a test contains `[Template]    Does Not Exist`
- **THEN** `Does Not Exist` gets one `argument` token

### Requirement: Test and keyword names

A test or task name SHALL get `testcaseName` tokens with the `declaration` modifier and a keyword name `keywordName` tokens with `declaration`. Variables in a test name and embedded arguments in a keyword name SHALL get `variable` tokens without `declaration`.

#### Scenario: Variable in a test name
- **WHEN** a test is named `Test With ${X} Var`
- **THEN** `Test With ` and ` Var` get `testcaseName` tokens with `declaration`, and `X` gets a `variable` token

#### Scenario: Keyword name
- **WHEN** a keyword is named `My Keyword`
- **THEN** `My Keyword` gets one `keywordName` token with `declaration`

### Requirement: Keyword calls

The keyword name of a call SHALL get a `keywordCall` token, with the `builtin` modifier exactly when it resolves to a BuiltIn keyword. A library, alias or resource prefix SHALL get a `namespace` token, with `builtin` for `BuiltIn`, and the dot an `operator` token. A prefix that names no import makes the whole cell one `keywordCall` token, and so does a keyword that does not resolve.

#### Scenario: BuiltIn keyword
- **WHEN** a test contains `Log    x`
- **THEN** `Log` gets a `keywordCall` token with the `builtin` modifier, and `x` gets none

#### Scenario: Prefix of a library alias
- **WHEN** `Library    String    AS    S` is imported and a test contains `S.Get Line Count    x`, on Robot Framework 6.0 or newer
- **THEN** `S` gets a `namespace` token, `.` an `operator` token and `Get Line Count` a `keywordCall` token

#### Scenario: Keyword that does not resolve
- **WHEN** a test contains `Unknown Keyword    x`
- **THEN** `Unknown Keyword` gets one `keywordCall` token, and `x` gets none

### Requirement: Arguments of keyword calls

Plain argument text, inline Python `${{ }}` and `$var` references in expressions SHALL get no tokens; variables in arguments SHALL get `variable` tokens. In a call of a keyword with embedded arguments, the fixed text SHALL get `keywordCall` tokens, an embedded value an `argument` token with the `embedded` modifier and a variable as value a `variable` token with `embedded`.

#### Scenario: Expression argument
- **WHEN** a test contains `Should Be True    $X == 'x'`
- **THEN** only `Should Be True` gets a token

#### Scenario: Embedded value
- **WHEN** a keyword `Add ${n}` exists and a test contains `Add 5`
- **THEN** `Add ` gets a `keywordCall` token and `5` an `argument` token with the `embedded` modifier

### Requirement: BDD prefixes

A `Given`, `When`, `Then`, `And` or `But` prefix in any case, and a localized prefix (Robot Framework 6.0 and newer), SHALL get a `bddPrefix` token when the keyword resolves without the prefix; the rest is rendered like a keyword call. When the keyword does not resolve, the whole cell SHALL get one `keywordCall` token.

#### Scenario: Prefix of a resolved keyword
- **WHEN** a test contains `Given Log    x`
- **THEN** `Given` gets a `bddPrefix` token and `Log` a `keywordCall` token with the `builtin` modifier

#### Scenario: Prefix of a keyword that does not resolve
- **WHEN** a test contains `Given Unknown Keyword`
- **THEN** `Given Unknown Keyword` gets one `keywordCall` token

#### Scenario: Localized prefix
- **WHEN** a file with `Language: German` contains `Angenommen Log    x`, on Robot Framework 6.0 or newer
- **THEN** `Angenommen` gets a `bddPrefix` token and `Log` a `keywordCall` token

### Requirement: Named arguments

When the keyword resolves and the name before `=` is one of its parameters, positional-only parameters aside, or the keyword accepts free named arguments, the name SHALL get a `namedArgument` token and `=` an `operator` token; the value gets no token except variables. The named-argument syntax SHALL NOT be split for an unresolved keyword, an escaped `\=`, a name that contains a variable, and the own arguments of a Run Keyword variant.

#### Scenario: Named argument
- **WHEN** a test contains `Log    msg    level=WARN`
- **THEN** `level` gets a `namedArgument` token and `=` an `operator` token, and `msg` and `WARN` get none

#### Scenario: Escaped equals sign
- **WHEN** a test contains `Log    level\=WARN`
- **THEN** no token of the argument is a `namedArgument` token

#### Scenario: Own argument of a Run Keyword variant
- **WHEN** a test contains `Repeat Keyword    repeat=2    Log    x`
- **THEN** `repeat=2` gets no token, as Robot Framework takes it as a literal value

### Requirement: Continuation markers

A continuation marker `...` outside documentation SHALL get a `continuation` token, also inside a multi-line inner call of a Run Keyword variant.

#### Scenario: Continuation line of an inner call
- **WHEN** a test contains `Run Keyword    Log` and the next line `...    x`
- **THEN** `...` gets a `continuation` token

### Requirement: Run Keyword variants

For the Run Keyword variants of BuiltIn, the outer keyword SHALL get a `keywordCall` token with `builtin` and the inner keyword a `keywordCallInner` token, with the `builtin` modifier, prefix and BDD tokens like a call; its arguments are rendered like call arguments, recursively for nested variants. Conditions, counts, timeouts and expected errors get no tokens except variables.

#### Scenario: Inner keyword with a prefix and a named argument
- **WHEN** a test contains `Run Keyword    BuiltIn.Log    a    level=WARN`
- **THEN** `Run Keyword` gets a `keywordCall` token with `builtin`, `BuiltIn` a `namespace` token with `builtin`, `.` an `operator` token, `Log` a `keywordCallInner` token with `builtin`, `level` a `namedArgument` token and `=` an `operator` token

#### Scenario: Inner keyword after fixed arguments
- **WHEN** a test contains `Wait Until Keyword Succeeds    2x    1s    Log    x`
- **THEN** `Log` gets a `keywordCallInner` token with `builtin`, and `2x` and `1s` get none

#### Scenario: Nested variants
- **WHEN** a test contains `Run Keyword    Run Keyword    Log    x`
- **THEN** the second `Run Keyword` and `Log` get `keywordCallInner` tokens with `builtin`

### Requirement: ELSE, ELSE IF and AND in Run Keyword variants

In `Run Keyword If` and `Run Keywords`, `ELSE`, `ELSE IF` and `AND` written in upper case SHALL get `controlFlow` tokens, also while the branch after them is still incomplete; `\AND` stays an argument.

#### Scenario: ELSE branch
- **WHEN** a test contains `Run Keyword If    ${c}    Log    a    ELSE    Log    b`
- **THEN** `ELSE` gets a `controlFlow` token and both `Log` get `keywordCallInner` tokens

#### Scenario: Incomplete ELSE
- **WHEN** a test contains `Run Keyword If    ${c}    Log    a    ELSE`
- **THEN** `ELSE` gets a `controlFlow` token

#### Scenario: AND
- **WHEN** a test contains `Run Keywords    No Operation    AND    Log    x`
- **THEN** `AND` gets a `controlFlow` token

### Requirement: Control structures

`FOR`, `END`, `IF`, `ELSE IF`, `ELSE`, `TRY`, `EXCEPT`, `FINALLY`, `WHILE`, `BREAK`, `CONTINUE`, `RETURN` and `GROUP` (Robot Framework 7.2 and newer) SHALL get `controlFlow` tokens, `IN`, `IN RANGE`, `IN ENUMERATE` and `IN ZIP` `forSeparator` tokens. Loop values, conditions, `EXCEPT` patterns and `GROUP` names SHALL get no tokens except variables. A word that Robot Framework rejects at its place, such as `END` outside a block, SHALL get an `error` token.

#### Scenario: FOR loop
- **WHEN** a test contains `FOR    ${i}    IN RANGE    3`
- **THEN** `FOR` gets a `controlFlow` token, `i` a `variable` token and `IN RANGE` a `forSeparator` token, and `3` gets none

#### Scenario: Condition
- **WHEN** an IF block contains `ELSE IF    ${x} == 2`
- **THEN** `ELSE IF` gets a `controlFlow` token and `x` a `variable` token

#### Scenario: END outside a block
- **WHEN** a test contains `END` without an open block
- **THEN** `END` gets an `error` token

### Requirement: Options only where Robot Framework reads them

A `start=`, `mode=` or `fill=` cell of a FOR loop and an `on_limit=` or `on_limit_message=` cell of a WHILE loop SHALL get the option token only where Robot Framework reads it as an option: `start` as the last value of `IN ENUMERATE`, `mode` and `fill` of `IN ZIP` from Robot Framework 6.1 on, and `on_limit` and `on_limit_message` from 6.1 on. Elsewhere such a cell gets no token.

#### Scenario: start of IN ENUMERATE
- **WHEN** a test contains `FOR    ${i}    ${x}    IN ENUMERATE    @{L}    start=1`
- **THEN** `start=1` gets one `controlFlow` token

#### Scenario: start in a plain FOR loop
- **WHEN** a test contains `FOR    ${i}    IN    start=1`
- **THEN** `start=1` gets no token

#### Scenario: on_limit before Robot Framework 6.1
- **WHEN** a test contains `WHILE    True    limit=3    on_limit=pass`, on Robot Framework 6.0 or older
- **THEN** `limit=3` gets one `controlFlow` token and `on_limit=pass` none

### Requirement: Inline IF

In an inline `IF`, the keywords of the branches SHALL be rendered like keyword calls, `ELSE IF` and `ELSE` SHALL get `controlFlow` tokens and an assignment target a `variable` token.

#### Scenario: Inline IF with assignment
- **WHEN** a test contains `${r}=    IF    ${True}    Set Variable    1    ELSE    Set Variable    2`
- **THEN** `r` gets a `variable` token, `IF` and `ELSE` `controlFlow` tokens, and both `Set Variable` `keywordCall` tokens with `builtin`

### Requirement: VAR and assignments without a keyword

`VAR` (Robot Framework 7.0 and newer) SHALL get a `var` token and the variable name a `variable` token, also when Robot Framework rejects the line or cannot resolve a nested name statically; values get no tokens except variables. A line with an assignment but no keyword, such as `${a}=`, SHALL get a `variable` token for the assigned name.

#### Scenario: VAR
- **WHEN** a test contains `VAR    ${x}    value`, on Robot Framework 7.0 or newer
- **THEN** `VAR` gets a `var` token and `x` a `variable` token, and `value` gets none

#### Scenario: VAR with a nested name
- **WHEN** a test contains `VAR    ${${x}}    v`, on Robot Framework 7.0 or newer
- **THEN** `VAR` gets a `var` token and `x` a `variable` token

#### Scenario: Assignment without a keyword
- **WHEN** a test contains `${a}=` without a keyword
- **THEN** `a` gets one `variable` token

### Requirement: Differences from the legacy path

Where the semantic-model analysis path and the legacy path render a construct differently, the semantic-model path SHALL send the tokens given in the scenarios of this requirement; the legacy path keeps its own until `semantic-model-cleanup` removes it.

#### Scenario: Return setting
- **WHEN** a keyword contains `[Return]    ${x}`
- **THEN** `Return` gets a `setting` token, where the legacy path sends `controlFlow`

#### Scenario: Setup keyword that does not resolve
- **WHEN** a test contains `[Setup]    Unknown Keyword`
- **THEN** `Unknown Keyword` gets one `keywordCall` token, where the legacy path sends `argument`

#### Scenario: Setup keyword from a variable
- **WHEN** a test contains `[Setup]    ${SETUP}`
- **THEN** `${SETUP}` gets one `keywordCall` token, where the legacy path sends `argument`

#### Scenario: WHILE limit before Robot Framework 6.1
- **WHEN** a test contains `WHILE    True    limit=3`, on Robot Framework 6.0 or older
- **THEN** `limit=3` gets one `controlFlow` token, where the legacy path sends none

#### Scenario: Assignment without a keyword on Robot Framework 6.0 and newer
- **WHEN** a test contains `${a}=` without a keyword, on Robot Framework 6.0 or newer
- **THEN** `a` gets one `variable` token, where the legacy path sends the same token twice

#### Scenario: BDD prefix of a keyword that does not resolve
- **WHEN** a test contains `Given Unknown Keyword`
- **THEN** it gets one `keywordCall` token, where the legacy path splits off `Given` as `bddPrefix`

#### Scenario: Name that matches with and without the BDD prefix
- **WHEN** keywords `Prefixed` and `Given Prefixed` exist and a test calls `Given Prefixed`, on Robot Framework 7.1 or newer
- **THEN** `Given` gets a `bddPrefix` token and `Prefixed` a `keywordCall` token, as Robot Framework calls `Prefixed`, where the legacy path renders the full name as one keyword

#### Scenario: Content of an invalid section on Robot Framework 6.1
- **WHEN** `*** Something ***` is followed by `here`, on Robot Framework 6.1
- **THEN** `here` gets a `comment` token, where the legacy path sends none before 7.0

#### Scenario: Comments of imports, template settings and documentation
- **WHEN** a file contains `Resource    res.resource    # c` and `[Documentation]    text    # c`
- **THEN** the first `# c` gets a `comment` token and the second none, where the legacy path does the opposite

#### Scenario: Escape in an import name
- **WHEN** a file contains `Resource    .\\res.resource`
- **THEN** `.\\res.resource` gets one `namespace` token, where the legacy path sends `escape` tokens for the escapes
