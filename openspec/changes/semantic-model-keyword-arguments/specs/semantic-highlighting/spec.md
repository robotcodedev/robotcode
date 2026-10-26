# Spec Delta

## MODIFIED Requirements

### Requirement: Keywords in settings

The keyword of a setup or teardown setting SHALL be rendered like a keyword call, a keyword name taken from a variable with only a `variable` token for the variable name, and `NONE` SHALL get one `argument` token. A resolved keyword of `Test Template` or `[Template]` SHALL be rendered like a keyword call, also when it resolves only with the values of the first data row, its placeholders then as `variable` tokens with `embedded`; a template name that does not resolve and `NONE` SHALL get one `argument` token over the cell.

#### Scenario: Setup
- **WHEN** a test contains `[Setup]    Log    x`
- **THEN** `Log` gets a `keywordCall` token with the `builtin` modifier

#### Scenario: NONE as teardown
- **WHEN** a test contains `[Teardown]    NONE`
- **THEN** `NONE` gets one `argument` token

#### Scenario: Template that does not resolve
- **WHEN** a test contains `[Template]    Does Not Exist`
- **THEN** `Does Not Exist` gets one `argument` token

#### Scenario: Setup keyword from a variable
- **WHEN** a test contains `[Setup]    ${SETUP}`
- **THEN** `SETUP` gets a `variable` token, and the rest of the cell gets no token

#### Scenario: Template that resolves with its data rows
- **WHEN** a keyword `The answer of everything should be 42` exists, and a test has `[Template]    The ${meaning} of ${life} should be 42` and the data row `answer    everything`
- **THEN** `The ` gets a `keywordCall` token, and `meaning` and `life` get `variable` tokens with the `embedded` modifier

### Requirement: Named arguments

When the keyword resolves and the name before `=` is a parameter that takes a name, or the keyword accepts free named arguments, the name SHALL get a `namedArgument` token and `=` an `operator` token; the value gets no token except variables. It SHALL NOT be split for an unresolved keyword, an escaped `\=`, a name that contains a variable and the own arguments of a registered run keyword. In template data rows, the name and `=` of such a cell SHALL get these tokens too, for the template keyword.

#### Scenario: Named argument
- **WHEN** a test contains `Log    msg    level=WARN`
- **THEN** `level` gets a `namedArgument` token and `=` an `operator` token, and `msg` and `WARN` get none

#### Scenario: Escaped equals sign
- **WHEN** a test contains `Log    level\=WARN`
- **THEN** no token of the argument is a `namedArgument` token

#### Scenario: Own argument of a Run Keyword variant
- **WHEN** a test contains `Repeat Keyword    repeat=2    Log    x`
- **THEN** `repeat=2` gets no token, as Robot Framework takes it as a literal value

#### Scenario: Name of a positional-only parameter
- **WHEN** a library keyword `Pos Only` takes `(a, b, /, c, d=1)` and a test contains `Pos Only    1    a=2    3`
- **THEN** no token of `a=2` is a `namedArgument` token, as Robot Framework passes it to `b` as it is

#### Scenario: Named argument in a template data row
- **WHEN** a test has `[Template]    Log` and the data row `hello    level=WARN`
- **THEN** `level` gets a `namedArgument` token and `=` an `operator` token

### Requirement: Run Keyword variants

For a keyword that runs other keywords, a BuiltIn Run Keyword variant, a keyword with `KeywordName` arguments (7.4 and newer) or a run keyword another library registers, the outer keyword SHALL be rendered like a call and the inner keyword like one with `keywordCallInner`; its arguments like call arguments, recursively. An inner keyword name from a variable SHALL get only a `variable` token for the name. Conditions, counts, timeouts and expected errors get no tokens except variables.

#### Scenario: Inner keyword with a prefix and a named argument
- **WHEN** a test contains `Run Keyword    BuiltIn.Log    a    level=WARN`
- **THEN** `Run Keyword` gets a `keywordCall` token with `builtin`, `BuiltIn` a `namespace` token with `builtin`, `.` an `operator` token, `Log` a `keywordCallInner` token with `builtin`, `level` a `namedArgument` token and `=` an `operator` token

#### Scenario: Inner keyword after fixed arguments
- **WHEN** a test contains `Wait Until Keyword Succeeds    2x    1s    Log    x`
- **THEN** `Log` gets a `keywordCallInner` token with `builtin`, and `2x` and `1s` get none

#### Scenario: Nested variants
- **WHEN** a test contains `Run Keyword    Run Keyword    Log    x`
- **THEN** the second `Run Keyword` and `Log` get `keywordCallInner` tokens with `builtin`

#### Scenario: Keyword-typed arguments
- **WHEN** a library keyword `Run It` takes `name: KeywordName, *args: KeywordArgument` and a test contains `Run It    Log    x`, on Robot Framework 7.4 or newer
- **THEN** `Log` gets a `keywordCallInner` token with `builtin`

#### Scenario: Registered run keyword
- **WHEN** a library registers its keyword `Run Twice`, which takes `(name, *args)`, as a run keyword whose first argument is the keyword name, and a test contains `Run Twice    Log    x`
- **THEN** `Log` gets a `keywordCallInner` token with `builtin`

#### Scenario: Inner keyword from a variable
- **WHEN** a test contains `Run Keyword    ${kw}    x`
- **THEN** `kw` gets a `variable` token, and the rest of the cell gets no token
