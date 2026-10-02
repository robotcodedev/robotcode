# Spec: intellij-syntax-highlighting

## Purpose

Defines how the IntelliJ plugin highlights Robot Framework files on every platform version it supports: with the TextMate grammar it bundles and the semantic tokens of the RobotCode language server, in the colours of the active colour scheme. It also defines how its lexers share the work of matching the grammar.

## Requirements

### Requirement: Robot Framework files are highlighted with the bundled grammar

The IntelliJ plugin SHALL highlight Robot Framework suite and resource files with the Robot Framework TextMate grammar it bundles (scope `source.robotframework`), in the editor and when it parses the file. It SHALL NOT bundle the grammar for Robot Framework code blocks in Markdown, which only the VS Code extension uses. The way the lexer is built SHALL NOT change which tokens a file is split into or which scopes they get.

#### Scenario: Suite file in the editor
- **WHEN** a `.robot` file with settings, variables, test cases, keywords and comments is opened in PyCharm or IntelliJ IDEA 2026.1
- **THEN** section headers, test case and keyword names, keyword calls, settings, variables and comments are highlighted with the colours of their scopes

#### Scenario: Same tokens after a change to the lexer construction
- **WHEN** the same Robot Framework files are lexed with the lexer before and after a change to how it is built
- **THEN** both produce the same tokens with the same offsets and scopes

### Requirement: The lexer uses no deprecated TextMate API of the supported platforms

The plugin SHALL build its TextMate lexer only from TextMate plugin API that is not deprecated in its minimum supported platform version, and SHALL use the replacement API where the minimum version already provides one.

#### Scenario: Plugin verification on the minimum and newer versions
- **WHEN** `verifyPlugin` checks the plugin against the minimum supported IDE version and the newer versions it is configured for
- **THEN** the report lists no deprecated TextMate API usage

#### Scenario: Compiler warnings
- **WHEN** the plugin is compiled against the minimum supported platform version
- **THEN** the compiler reports no deprecation warning for TextMate API

### Requirement: Lexers share their caches

All Robot Framework lexers of one IDE instance SHALL share one cache of compiled regular expressions, one cache of selector weights and one cache of rule matches, instead of each lexer starting with empty caches. Concurrent use from several editors and background parses SHALL be safe.

#### Scenario: Second file reuses compiled patterns
- **WHEN** a second Robot Framework file is opened while the first one is still open
- **THEN** its highlighter reuses the regular expressions already compiled for the first file instead of compiling them again

#### Scenario: Highlighter and parser share caches
- **WHEN** a Robot Framework file is highlighted and parsed
- **THEN** the highlighting lexer and the parsing lexer use the same caches

### Requirement: Highlighting colours come from the active colour scheme

The IntelliJ plugin SHALL NOT ship its own colours for Robot Framework tokens. Every Robot Framework colour setting SHALL inherit from one of the IDE's general language colours (keyword, string, function declaration, field, comment and so on). That way every colour scheme, including third-party schemes that know nothing about Robot Framework, colours Robot Framework files. Colours a user sets on the Robot Framework colour settings page SHALL take precedence over the inherited ones.

#### Scenario: Third-party colour scheme
- **WHEN** a Robot Framework file is opened with a colour scheme that defines no Robot Framework colours
- **THEN** each token class is shown in that scheme's colour for the corresponding general language colour

#### Scenario: Switching the colour scheme
- **WHEN** the user switches to another colour scheme
- **THEN** the Robot Framework colours follow the new scheme's general language colours, and no Robot Framework token keeps a colour that only the plugin defines

#### Scenario: User-defined colour
- **WHEN** the user has set their own colour for a Robot Framework token class in their colour scheme
- **THEN** that colour is used instead of the inherited one

### Requirement: Token classes inherit from matching general language colours

Each Robot Framework colour setting SHALL inherit from the general language colour that matches the category the VS Code extension gives the token, so that the plugin makes no assumption about any particular colour scheme:
- keyword calls, test case names and keyword names inherit from *Function declaration*, so keyword calls look like keyword and test case names;
- variables inherit from *Instance field*;
- arguments inherit from *String*;
- section headers, settings, control flow, `VAR` and BDD prefixes inherit from *Keyword*.

Whether and how a general language colour is coloured is up to the colour scheme.

#### Scenario: Inheritance on the colour settings page
- **WHEN** the user selects "Keyword call" and then "Variable" on the Robot Framework colour settings page of an unmodified scheme
- **THEN** "Keyword call" inherits from the language default *Function declaration*, and "Variable" from *Instance field*

#### Scenario: Scheme that colours both categories
- **WHEN** the active scheme gives *Function declaration* and *Instance field* different colours, and a test case containing `Log    ${message}` is shown
- **THEN** `Log` has the function declaration colour and `${message}` has the instance field colour

#### Scenario: Scheme that leaves a category uncoloured
- **WHEN** the active scheme gives *Function declaration* no colour of its own
- **THEN** keyword calls are shown as plain text, like function names in the scheme's other languages

#### Scenario: BDD prefix
- **WHEN** a step `Given the user is logged in` is shown
- **THEN** `Given` has the keyword colour and the rest of the step has the keyword call colour

### Requirement: Variable names keep their look and delimiters look like brackets

The name of a variable SHALL have the variable look, and that look SHALL NOT change when semantic highlighting from the language server is applied on top of the grammar-based highlighting.

The delimiters of a variable are brackets, not part of its name. Each delimiter SHALL have its own Robot Framework colour setting that inherits from a general language colour for brackets, and the grammar-based highlighting SHALL draw it with that setting:
- "Variable begin" and "Variable end" (`${`, `@{`, `&{`, `%{`, `}` and the `$` of a bare `$name` in an expression), as well as "Expression begin" and "Expression end" (`${{`, `}}`), inherit from *Braces*;
- "Variable index begin" and "Variable index end" (the brackets of an item assignment such as `${DICT}[key]=`) inherit from *Brackets*.

#### Scenario: Variables section (issue #655)
- **WHEN** the line `${PAGE_OBJECT}    ${NONE}` in a `*** Variables ***` section is shown
- **THEN** `PAGE_OBJECT` and `NONE` have the variable look before and after semantic highlighting is applied

#### Scenario: Delimiter settings on the colour settings page
- **WHEN** the user selects "Variable begin" on the Robot Framework colour settings page of an unmodified scheme
- **THEN** it inherits from the language default *Braces*

#### Scenario: Bare variable in a condition
- **WHEN** `IF    $count > 1` is shown
- **THEN** `$` has the "Variable begin" look and `count` has the variable look

### Requirement: Semantic highlighting only adds what the colour scheme defines

Semantic highlighting from the language server SHALL change a token only in those text attributes (foreground, background, font style, effects such as underline or strikethrough) that the active colour scheme, or the user, defines for the token's colour setting or for a general language colour it inherits from. If nothing along that chain defines anything, the token SHALL keep its grammar-based look. This matches how VS Code combines semantic and grammar-based styles.

A change of the colour scheme, or of a colour setting, SHALL take effect in open files without reopening them.

#### Scenario: Category the scheme leaves undefined
- **WHEN** the active scheme defines nothing for *Class reference*, the general language colour namespaces inherit from, and `BuiltIn.Log    message` is shown
- **THEN** `BuiltIn` keeps the keyword call look it gets from the grammar after semantic highlighting is applied

#### Scenario: Style without a colour
- **WHEN** the user sets only *Italic* for "Named argument", without a foreground colour, and `Log    message    level=INFO` is shown
- **THEN** `level` keeps its grammar-based colour and is shown in italic

#### Scenario: Colour and effect set by the user
- **WHEN** the user sets a red foreground and an underline effect for "Namespace"
- **THEN** `BuiltIn` in `BuiltIn.Log` is shown red and underlined

#### Scenario: Scheme switch with open files
- **WHEN** the user switches the colour scheme, or changes and applies a Robot Framework colour, while a Robot Framework file is open
- **THEN** the semantic highlighting in that file follows the new settings without reopening the file

### Requirement: Grammar scopes without a Robot Framework colour

Some grammar scopes have no Robot Framework colour setting, for example the Python expressions in `IF` and `WHILE` conditions or regular expressions. A token with such a scope SHALL be coloured with the general language colour whose scope prefix is the longest one matching the start of the token's scope name. When a token carries several scope names, the innermost one with a match SHALL decide. A token without any match SHALL be shown as plain text.

#### Scenario: Operator and number in a condition
- **WHEN** `IF    $count > 1` is shown
- **THEN** `>` has the operator colour, not the keyword colour, and `1` has the number colour

#### Scenario: String in a condition
- **WHEN** `IF    "a" in $items` is shown
- **THEN** `"a"`, quotes included, has the string colour

#### Scenario: Scope without a match
- **WHEN** a token's scope names match no general language colour
- **THEN** the token is shown as plain text

### Requirement: Every semantic token type has a colour setting

Every semantic token type and modifier combination the RobotCode language server sends SHALL map to a Robot Framework colour setting or to a general language colour:
- language configuration lines (for example `Language: German` before the first section) SHALL get the comment colour;
- escape sequences in import names SHALL get the escape colour;
- embedded argument values in keyword calls SHALL get the embedded argument setting, which by default inherits the variable colour.

A token type the plugin does not know SHALL be left to the grammar-based highlighting, and SHALL NOT write a log entry for every token of that type.

#### Scenario: Language configuration line
- **WHEN** a file starting with `Language: German` is shown
- **THEN** that line has the comment colour

#### Scenario: Escape in an import name
- **WHEN** `Library    my\\lib.py` is shown
- **THEN** the escape sequence `\\` has the escape colour and the rest of the name has the namespace colour

#### Scenario: Embedded argument in a keyword call
- **WHEN** a call `My Keyword With ${count} Items` uses a keyword with an embedded argument
- **THEN** `${count}` has the embedded argument colour, which is the variable colour unless the user changed it

#### Scenario: Unknown token type
- **WHEN** the language server sends a token type the plugin has no mapping for
- **THEN** the grammar-based colour stays, and the IDE log gets at most one entry for that type
