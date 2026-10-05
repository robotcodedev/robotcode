# Spec Delta

## MODIFIED Requirements

### Requirement: Variable names keep their look and delimiters look like brackets

The name of a variable SHALL have the variable look, and that look SHALL NOT change when semantic highlighting from the language server is applied on top of the grammar-based highlighting.

The delimiters of a variable are brackets, not part of its name. Each delimiter SHALL have its own Robot Framework colour setting that inherits from a general language colour for brackets, and the grammar-based highlighting SHALL draw it with that setting:
- "Variable begin" and "Variable end" (`${`, `@{`, `&{`, `%{`, `}` and the `$` of a bare `$name` in an expression), as well as "Expression begin" and "Expression end" (`${{`, `}}`), inherit from *Braces*;
- "Variable index begin" and "Variable index end" (the brackets of an item assignment such as `${DICT}[key]=`) inherit from *Brackets*.

The delimiters SHALL keep that look when semantic highlighting is applied.

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

### Requirement: Every semantic token type has a colour setting

Every semantic token type and modifier combination the RobotCode language server sends SHALL map to a Robot Framework colour setting or to a general language colour:
- language configuration lines (for example `Language: German` before the first section) SHALL get the comment colour;
- escape sequences in import names SHALL get the escape colour;
- embedded argument values in keyword calls SHALL get the embedded argument setting, which by default inherits the variable colour. For a variable as the value, that is its name.

A token type the plugin does not know SHALL be left to the grammar-based highlighting, and SHALL NOT write a log entry for every token of that type.

#### Scenario: Language configuration line
- **WHEN** a file starting with `Language: German` is shown
- **THEN** that line has the comment colour

#### Scenario: Escape in an import name
- **WHEN** `Library    my\\lib.py` is shown
- **THEN** the escape sequence `\\` has the escape colour and the rest of the name has the namespace colour

#### Scenario: Embedded argument in a keyword call
- **WHEN** a call `My Keyword With ${count} Items` uses a keyword with an embedded argument
- **THEN** `count` has the embedded argument colour, which is the variable colour unless the user changed it, and `${` and `}` keep the "Variable begin" and "Variable end" look

#### Scenario: Unknown token type
- **WHEN** the language server sends a token type the plugin has no mapping for
- **THEN** the grammar-based colour stays, and the IDE log gets at most one entry for that type
