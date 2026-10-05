# Spec Delta: textmate-grammar

## Purpose

Defines what RobotCode's TextMate grammars for Robot Framework recognize, that they tokenize alike in every engine that uses them, and that the grammars for Robot Framework files, Markdown code blocks and REPL input come from one template. The grammars are the only highlighting where semantic tokens are missing: in Markdown views, on the documentation site, in REPL scripts and notebook cells, and in the editors before the language server answers.

## ADDED Requirements

### Requirement: All grammars come from one template

RobotCode's TextMate grammars for Robot Framework files, for Robot Framework code blocks in Markdown, and for REPL scripts and notebook cells SHALL be generated from one template. The REPL grammar SHALL recognize statements without indentation and without sections. Apart from that, every grammar SHALL give a statement the same scopes.

#### Scenario: Assignments in a REPL script
- **WHEN** a REPL script contains `${a}    ${b}=    Evaluate    (1, 2)`
- **THEN** `${a}` and `${b}` are variables, `=` is an operator, `Evaluate` is a keyword call and `(1, 2)` is an argument, as in the body of a test

#### Scenario: Control words in a notebook cell
- **WHEN** a notebook cell contains a `GROUP` block with `BREAK`, `CONTINUE` or `RETURN` statements
- **THEN** `GROUP`, `BREAK`, `CONTINUE`, `RETURN` and `END` are highlighted as control flow

### Requirement: The grammar tokenizes alike in every engine

The grammar for Robot Framework files SHALL give every non-whitespace character the same scopes in VS Code, in Shiki with its JavaScript regular expression engine, and in the TextMate engine of the oldest IntelliJ platform version the plugin supports. Every regular expression of the grammar SHALL compile in these engines in the form in which each engine uses it.

#### Scenario: RobotCode's test data
- **WHEN** the `.robot` and `.resource` files under `tests/` are tokenized in the three engines
- **THEN** every non-whitespace character gets the same scopes in all three, even where an engine splits the tokens differently

#### Scenario: A rule added to the template
- **WHEN** a rule is added to the template and the grammars are regenerated
- **THEN** its regular expressions compile in VS Code's Oniguruma, in Shiki's JavaScript engine in strict mode and in IntelliJ's Joni engine

### Requirement: Statement markers

At the start of a statement, the markers `IF`, `ELSE IF`, `ELSE`, `WHILE`, `FOR`, `TRY`, `EXCEPT`, `FINALLY`, `GROUP`, `END`, `BREAK`, `CONTINUE` and `RETURN`, in exact upper case, SHALL be highlighted as control flow. In a `FOR`, the first `IN`, `IN RANGE`, `IN ENUMERATE` or `IN ZIP` SHALL be highlighted as the loop separator, also on a continuation line, and every later cell as a value. In an `EXCEPT`, the first `AS` SHALL be highlighted as a marker and the cell after it as the variable.

#### Scenario: RETURN
- **WHEN** a keyword contains `RETURN    ${result}`
- **THEN** `RETURN` is highlighted as control flow, not as a keyword call

#### Scenario: FOR separator
- **WHEN** a test contains `FOR    ${i}    IN RANGE    3` and the loop body contains `Log    ${i}    IN`
- **THEN** `IN RANGE` is highlighted as the loop separator, and the `IN` in the body is an argument

#### Scenario: Separator on a continuation line
- **WHEN** `FOR    ${i}` is followed by `...    IN ENUMERATE    @{items}`
- **THEN** `IN ENUMERATE` is highlighted as the loop separator

#### Scenario: EXCEPT AS
- **WHEN** a test contains `EXCEPT    boom    AS    ${error}`
- **THEN** `boom` is an argument, `AS` is a marker and `${error}` is a variable

### Requirement: Variables in arguments

An environment variable SHALL end at its first closing brace, with an optional default value after `=`. Item access directly after a `$`, `@` or `&` variable SHALL be highlighted as part of that variable, with its brackets as index brackets; after an environment variable it SHALL stay text. Variable names in `$name` expressions of conditions SHALL include non-ASCII letters.

#### Scenario: Environment variable followed by another cell
- **WHEN** a test contains `Log    %{HOME}    level=INFO`
- **THEN** `%{HOME}` is an environment variable and `level=INFO` is an argument

#### Scenario: Environment variable with a default
- **WHEN** a test contains `Log    %{MISSING=default}`
- **THEN** `MISSING` is the variable name, `=` an operator and `default` the default value

#### Scenario: Item access
- **WHEN** a test contains `Log    ${DICT}[key][${i}]    @{LIST}[0]`
- **THEN** `[` and `]` are index brackets, `key` and `0` are index values, and `${i}` is a variable

#### Scenario: Brackets after an environment variable
- **WHEN** a test contains `Log    %{X}[0]`
- **THEN** `[0]` is plain text after the environment variable

#### Scenario: Non-ASCII name in a condition
- **WHEN** a test contains `IF    $größe > 1`
- **THEN** all of `größe` is the variable name, in VS Code and in IntelliJ

### Requirement: Comments after the first cell

A cell that starts with `#` after a separator SHALL be a comment up to the end of the line, also when it directly follows the first cell of a statement.

#### Scenario: Comment after a marker or a keyword
- **WHEN** a test contains `END    # loop ends` and `No Operation    # placeholder`
- **THEN** `# loop ends` and `# placeholder` are comments

### Requirement: Settings

In the `Library` setting and its translations, `AS` or `WITH NAME` followed by exactly one more cell on the same line SHALL be highlighted as the alias marker. In the `[Arguments]` setting and its translations, an `=` directly after a variable SHALL be highlighted as an operator before the default value. The brackets of `[Documentation]` SHALL be highlighted like those of the other test and keyword settings.

#### Scenario: Library alias
- **WHEN** the settings contain `Library    Collections    AS    Coll` and `Library    String    WITH NAME    Str`
- **THEN** `AS` and `WITH NAME` are alias markers

#### Scenario: AS without an alias
- **WHEN** the settings contain `Library    OperatingSystem    AS` with no cell after `AS`
- **THEN** `AS` is an argument

#### Scenario: Default values of arguments
- **WHEN** a keyword contains `[Arguments]    ${a}    ${b}=default    ${c}=${DEFAULT}`
- **THEN** each `=` after `${b}` and `${c}` is an operator, `default` is a value and `${DEFAULT}` a variable

### Requirement: Patterns of embedded arguments

Braces in the regular expression of an embedded argument SHALL belong to the pattern, so the embedded argument ends at its own closing brace.

#### Scenario: Quantifier in a pattern
- **WHEN** a keyword is named `Number ${n:\d{2}} Keyword`
- **THEN** `\d{2}` is the pattern of `${n}`, the brace after it ends the variable, and `Keyword` belongs to the keyword name
