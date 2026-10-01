# Spec Delta

## Purpose

Defines which semantic tokens the RobotCode language server sends for Robot Framework files. It sends only the information the TextMate grammar cannot derive from the text, rendered from the semantic model without decisions of its own.

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

### Requirement: Variables get a token for their name only

For every variable reference and every variable definition, the language server SHALL send one semantic token per variable name, carrying the modifiers the analyzer computed for that variable. It SHALL NOT send tokens for:
- the prefix (`$`, `@`, `&`, `%`);
- the braces;
- item-access brackets;
- the `=` of an assignment;
- the delimiters of an inline Python expression.

This SHALL hold at every site where Robot Framework defines or uses variables:
- declarations in `*** Variables ***`;
- keyword-call assignments, including several targets and item assignments such as `${DICT}[key]=`;
- `VAR`, `FOR` loop variables and `EXCEPT ... AS` targets;
- `[Arguments]` parameters, including parameters with default values;
- embedded arguments in keyword names and calls;
- usages in arguments and settings, including nested variables, item access and environment variables.

#### Scenario: Declarations in the Variables section
- **WHEN** the line `${PAGE_OBJECT}    ${NONE}` in a `*** Variables ***` section is analyzed
- **THEN** the only tokens on the line are for `PAGE_OBJECT` and `NONE`

#### Scenario: Variable inside an argument
- **WHEN** `Log    Hello ${name}!` is analyzed
- **THEN** `Log` gets a keyword-call token, `name` gets a variable token, and `Hello `, `${`, `}` and `!` get no token

#### Scenario: Item assignment
- **WHEN** `${DICT}[key]=    Set Variable    x` is analyzed
- **THEN** `DICT` gets a variable token, and `${`, `}`, `[key]` and `=` get no token

#### Scenario: Parameter with a default value
- **WHEN** `[Arguments]    ${opt}=default` is analyzed
- **THEN** `opt` gets a variable token, and neither `=` nor `default` gets one

#### Scenario: Nested variable
- **WHEN** `Log    ${NESTED_${SCALAR}}` is analyzed
- **THEN** `NESTED_` and `SCALAR` get variable tokens and none of the four braces does

#### Scenario: Environment variable with a default value
- **WHEN** `Log    %{MISSING=default}` is analyzed
- **THEN** `MISSING` gets a variable token, and `%{`, `=`, `default` and `}` get no token

#### Scenario: Inline Python expression
- **WHEN** `Log    ${{ len($LIST) }}` is analyzed
- **THEN** no token is sent for any part of `${{ len($LIST) }}`

#### Scenario: Modifiers on the name
- **WHEN** a reference to `${CURDIR}` is analyzed
- **THEN** the modifiers of that variable, such as the builtin type modifier, are on the token for `CURDIR`

### Requirement: No token for the BDD separator

The language server SHALL NOT send a semantic token for the whitespace between a BDD prefix (`Given`, `When`, `Then`, `And`, `But`, or a localized prefix) and the keyword name. This applies in keyword calls, in setup, teardown and template settings, and in the inner calls of Run Keyword variants.

#### Scenario: Step with a BDD prefix
- **WHEN** `Given the user is logged in` is analyzed
- **THEN** `Given` gets a BDD-prefix token, `the user is logged in` gets a keyword-call token, and the space between them gets no token

#### Scenario: Setup with a BDD prefix
- **WHEN** `[Setup]    Given the user is logged in` is analyzed
- **THEN** the space between `Given` and `the user is logged in` gets no token

### Requirement: Every variable form is highlighted with its parts

Every form in which Robot Framework declares or uses a variable SHALL be highlighted with its parts distinguished:
- prefix and braces;
- name;
- item-access brackets;
- type hint;
- default value;
- embedded-argument pattern.

The TextMate grammar SHALL do this where the parts can be told apart from the text alone. Semantic tokens SHALL do it where only the analysis can tell them apart.

#### Scenario: Environment variable followed by more text
- **WHEN** `Log    %{HOME} and %{MISSING=default}` is highlighted
- **THEN** both `%{`…`}` pairs are recognized as environment variables, with `HOME` and `MISSING` as their names and ` and ` as argument text

#### Scenario: Item access in an argument
- **WHEN** `Log    ${LIST}[0]` is highlighted
- **THEN** `[` and `]` are highlighted as item-access brackets, not as argument text

#### Scenario: Type hint
- **WHEN** `[Arguments]    ${count: int}` or `${count: int}=    Get Count` is highlighted
- **THEN** `count` is highlighted as the variable name and `int` as a type

### Requirement: Inner keyword calls of Run Keyword variants render as keywords

For keywords of the Run Keyword family, the language server SHALL send keyword tokens, with their own modifiers, for the keyword names inside the arguments, and control-flow tokens for `ELSE`, `ELSE IF` and `AND`. Tokens SHALL be sent in strictly ascending positions.

#### Scenario: Run Keyword If branches
- **WHEN** `Run Keyword If    ${cond}    Log    a    ELSE    My KW    b` is analyzed
- **THEN** `Log` and `My KW` get keyword tokens, `ELSE` gets a control-flow token, and the token positions ascend strictly

### Requirement: Modifiers come from the analysis

Semantic-token modifiers SHALL be computed when the file is analyzed and carried in the semantic model, and rendering SHALL map them without resolving anything again. This covers built-in keywords and namespaces, embedded arguments, declarations and variable type modifiers.

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
