# Spec Delta

## MODIFIED Requirements

### Requirement: Token classes inherit from matching general language colours

Each Robot Framework colour setting SHALL inherit from the general language colour that matches the category the VS Code extension gives the token, so that the plugin makes no assumption about any particular colour scheme:
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

#### Scenario: Variables section (issue #655)
- **WHEN** the line `${PAGE_OBJECT}    ${NONE}` in a `*** Variables ***` section is shown
- **THEN** `PAGE_OBJECT` and `NONE` have the variable look before and after semantic highlighting is applied

#### Scenario: Delimiters after semantic highlighting (issue #655)
- **WHEN** the line `${PAGE_OBJECT}    ${NONE}` in a `*** Variables ***` section is shown and semantic highlighting has been applied
- **THEN** each `${` has the "Variable begin" look and each `}` has the "Variable end" look

#### Scenario: Delimiter settings on the colour settings page
- **WHEN** the user selects "Variable begin" on the Robot Framework colour settings page of an unmodified scheme
- **THEN** it inherits from the language default *Braces*

#### Scenario: Bare variable in a condition
- **WHEN** `IF    $count > 1` is shown
- **THEN** `$` has the "Variable begin" look and `count` has the variable look

### Requirement: Semantic highlighting only adds what the colour scheme defines

Semantic highlighting from the language server SHALL change a token only in those text attributes (foreground, background, font style, effects such as underline or strikethrough) that its colour setting brings from the active colour scheme, from the user, or from a general language colour it inherits from.

A change of the colour scheme, or of a colour setting, SHALL take effect in open files without reopening them.

#### Scenario: Refining token with an undefined colour
- **WHEN** the active scheme defines nothing for "Variable" and *Instance field*, the general language colour it inherits from, and `Log    ${name}` is shown
- **THEN** `name` keeps the variable look it gets from the grammar after semantic highlighting is applied

#### Scenario: Category the scheme leaves undefined
- **WHEN** the active scheme defines nothing for *Class reference*, the general language colour namespaces inherit from, and `BuiltIn.Log    message` is shown
- **THEN** `BuiltIn` has the plain-text look instead of the keyword call look it gets from the grammar

#### Scenario: Type hint with a plain-text colour
- **WHEN** the active scheme defines nothing for *Class reference*, and `${count: int}=    Set Variable    1` is shown with Robot Framework 7.3 or later
- **THEN** `int` has the plain-text look, and `count` keeps the variable look

#### Scenario: Style without a colour
- **WHEN** the user sets only *Italic* for "Named argument", without a foreground colour, and `Log    message    level=INFO` is shown
- **THEN** `level` keeps its grammar-based colour and is shown in italic

#### Scenario: Colour and effect set by the user
- **WHEN** the user sets a red foreground and an underline effect for "Namespace"
- **THEN** `BuiltIn` in `BuiltIn.Log` is shown red and underlined

#### Scenario: Scheme switch with open files
- **WHEN** the user switches the colour scheme, or changes and applies a Robot Framework colour, while a Robot Framework file is open
- **THEN** the semantic highlighting in that file follows the new settings without reopening the file

### Requirement: Every semantic token type has a colour setting

Every semantic token type and modifier combination the RobotCode language server sends SHALL map to a Robot Framework colour setting or to a general language colour:
- language configuration lines (for example `Language: German` before the first section) SHALL get the comment colour;
- escape sequences in import names SHALL get the escape colour.

#### Scenario: Language configuration line
- **WHEN** a file starting with `Language: German` is shown
- **THEN** that line has the comment colour

#### Scenario: Escape in an import name
- **WHEN** `Library    my\\lib.py` is shown
- **THEN** the escape sequence `\\` has the escape colour and the rest of the name has the namespace colour

#### Scenario: Embedded argument in a keyword call
- **WHEN** a call `My Keyword With ${count} Items` uses a keyword with an embedded argument
- **THEN** `count` has the embedded argument colour, which is the variable colour unless the user changed it, and `${` and `}` keep the "Variable begin" and "Variable end" look

#### Scenario: Parameter and type hint settings on the colour settings page
- **WHEN** the user selects "Parameter" or "Type hint" on the Robot Framework colour settings page of an unmodified scheme
- **THEN** "Parameter" inherits from the Robot Framework setting "Variable" and "Type hint" from the language default *Class reference*

#### Scenario: Parameter with a colour of its own
- **WHEN** the active scheme gives "Parameter" a colour of its own and a keyword with `[Arguments]    ${count}` is shown
- **THEN** `count` has that colour after semantic highlighting, and `${` and `}` keep the "Variable begin" and "Variable end" look

#### Scenario: Parameter by default
- **WHEN** neither "Parameter" nor "Variable" is changed, and a keyword with `[Arguments]    ${count}` is shown
- **THEN** `count` has the variable look in the editor and in the preview of the colour settings page

#### Scenario: Unknown token type
- **WHEN** the language server sends a token type the plugin has no mapping for
- **THEN** the grammar-based colour stays, and the IDE log gets at most one entry for that type

## ADDED Requirements

### Requirement: Keyword calls and names inherit from Function declaration

Keyword calls, test case names and keyword names SHALL inherit from *Function declaration*, so keyword calls look like keyword and test case names.

#### Scenario: Name settings on the colour settings page
- **WHEN** the user selects "Test case name" and then "Keyword name" on the Robot Framework colour settings page of an unmodified scheme
- **THEN** both inherit from the language default *Function declaration*

### Requirement: Variable delimiters look like brackets

The delimiters of a variable are brackets, not part of its name. Each delimiter SHALL have its own Robot Framework colour setting that inherits from a general language colour for brackets, and the grammar-based highlighting SHALL draw it with that setting. The delimiters SHALL keep that look when semantic highlighting is applied.

#### Scenario: Delimiters in a keyword call
- **WHEN** `Log    ${name}` is shown and semantic highlighting has been applied
- **THEN** `${` has the "Variable begin" look and `}` has the "Variable end" look

### Requirement: Colour settings of the variable delimiters

The colour settings of the variable delimiters SHALL inherit as follows:
- "Variable begin" and "Variable end" (`${`, `@{`, `&{`, `%{`, `}` and the `$` of a bare `$name` in an expression), as well as "Expression begin" and "Expression end" (`${{`, `}}`), inherit from *Braces*;
- "Variable index begin" and "Variable index end" (the brackets of an item assignment such as `${DICT}[key]=`) inherit from *Brackets*.

#### Scenario: Index delimiter on the colour settings page
- **WHEN** the user selects "Variable index begin" on the Robot Framework colour settings page of an unmodified scheme
- **THEN** it inherits from the language default *Brackets*

### Requirement: Refining tokens keep the grammar-based look

Where a token only refines what the grammar-based highlighting already shows, it SHALL keep its grammar-based look if nothing along that chain defines more than the plain-text look. This applies to variables, including embedded argument values, parameters, section headers, settings, `VAR`, `FOR` separators, test and keyword names, continuation markers, comments, language configuration lines and escapes. It matches how VS Code combines semantic and grammar-based styles.

#### Scenario: Parameter with an undefined colour
- **WHEN** the active scheme defines nothing for "Parameter", "Variable" and *Instance field*, and a keyword with `[Arguments]    ${count}` is shown
- **THEN** `count` keeps the variable look it gets from the grammar after semantic highlighting is applied

### Requirement: Correcting tokens apply their colour setting

Where a token corrects what the grammar-based highlighting shows, its colour setting SHALL apply even if it resolves to the plain-text look, because the grammar-based look belongs to another category there. This applies to type hints, named arguments, namespaces, operators, keyword calls, BDD prefixes, arguments, control-flow words and options, and errors. A token type the plugin does not list as correcting SHALL be treated as refining.

#### Scenario: Keyword call with a plain-text colour
- **WHEN** the active scheme gives *Function declaration* no colour of its own, and `Log    message` is shown
- **THEN** `Log` has the plain-text look after semantic highlighting is applied

### Requirement: Colour settings of embedded arguments, parameters and type hints

Embedded argument values in keyword calls SHALL get the embedded argument setting, which by default inherits the variable colour. For a variable as the value, that is its name. The names of arguments declared in `[Arguments]` SHALL get the "Parameter" setting, which inherits from the Robot Framework setting "Variable". Type hints of variables SHALL get the "Type hint" setting, which inherits from the general language colour *Class reference*.

#### Scenario: Type hint by default
- **WHEN** neither "Type hint" nor *Class reference* is changed in a scheme that colours *Class reference*, and `${count: int}=    Set Variable    1` is shown with Robot Framework 7.3 or later
- **THEN** `int` has the class reference colour

### Requirement: Unknown token types are left to the grammar

A token type the plugin does not know SHALL be left to the grammar-based highlighting, and SHALL NOT write a log entry for every token of that type.

#### Scenario: Many tokens of an unknown type
- **WHEN** the language server sends many tokens of a type the plugin has no mapping for in one file
- **THEN** each keeps its grammar-based colour, and the IDE log gets at most one entry for that type
