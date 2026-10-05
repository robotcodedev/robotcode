# Spec Delta

## ADDED Requirements

### Requirement: Semantic tokens only add what the grammar cannot know

The language server SHALL send semantic tokens only for information that the Robot Framework TextMate grammar cannot derive from the text alone. Examples are whether a cell is a keyword call or an argument, namespaces, built-in keywords, embedded arguments, declarations, named arguments, and variable names with their resolution.

It SHALL NOT send semantic tokens for:
- documentation text and comments;
- Python expressions, in `IF` and `WHILE` conditions as well as inside `${{ }}`;
- separators and other whitespace.

#### Scenario: Keyword call with an argument
- **WHEN** `Log    message` is analyzed
- **THEN** `Log` gets a keyword-call token and `message` gets no token

#### Scenario: Template data row
- **WHEN** a test case with `[Template]    Log` contains the data row `hello    WARN`
- **THEN** `hello` and `WARN` get argument tokens, because the grammar cannot tell a template row from a keyword call

#### Scenario: Documentation and comments
- **WHEN** a keyword contains `[Documentation]    Does *things*`, a comment line `# note`, and `Log    x    # trailing`
- **THEN** neither the documentation text nor either comment gets a token

#### Scenario: Python expression in a condition
- **WHEN** `IF    $count > 1` is analyzed
- **THEN** `IF` gets a control-flow token, and `$count`, `>` and `1` get no token

### Requirement: No token for the BDD separator

The language server SHALL NOT send a semantic token for the whitespace between a BDD prefix (`Given`, `When`, `Then`, `And`, `But`, or a localized prefix) and the keyword name. This applies in keyword calls, in setup, teardown and template settings, and in the inner calls of Run Keyword variants.

#### Scenario: Step with a BDD prefix
- **WHEN** `Given the user is logged in` is analyzed
- **THEN** `Given` gets a BDD-prefix token, `the user is logged in` gets a keyword-call token, and the space between them gets no token

#### Scenario: Setup with a BDD prefix
- **WHEN** `[Setup]    Given the user is logged in` is analyzed
- **THEN** the space between `Given` and `the user is logged in` gets no token

### Requirement: Inner keyword calls of Run Keyword variants render as keywords

For keywords of the Run Keyword family, the language server SHALL send keyword tokens, with their own modifiers, for the keyword names inside the arguments, and control-flow tokens for `ELSE`, `ELSE IF` and `AND`. Tokens SHALL be sent in strictly ascending positions.

#### Scenario: Run Keyword If branches
- **WHEN** `Run Keyword If    ${cond}    Log    a    ELSE    My KW    b` is analyzed
- **THEN** `Log` and `My KW` get keyword tokens, `ELSE` gets a control-flow token, and the token positions ascend strictly

### Requirement: Modifiers come from the analysis

Semantic-token modifiers SHALL be computed when the file is analyzed and carried in the semantic model, and rendering SHALL map them without resolving anything again. This covers built-in keywords and namespaces, embedded arguments, declarations and the builtin modifier of variables.

#### Scenario: BuiltIn keyword
- **WHEN** a `BuiltIn.Log` call is analyzed
- **THEN** the keyword token carries the builtin modifier taken from the semantic model, and rendering does not look up the keyword

### Requirement: Rendering makes no semantic decisions of its own

Rendering semantic tokens from the semantic model SHALL contain:
- no Robot Framework version checks;
- no tokenization or parsing of token values;
- no classification by statement type.

The analyzer SHALL make all semantic decisions when it builds the model: token kinds, splits, modifiers and version differences. Rendering SHALL map token kinds and modifiers through static tables and the rules of this capability.

#### Scenario: Version-specific construct
- **WHEN** a file uses a version-specific construct such as `*** Tasks ***`, `VAR` or `AS` on a library import
- **THEN** its tokens are rendered without the rendering consulting the Robot Framework version
