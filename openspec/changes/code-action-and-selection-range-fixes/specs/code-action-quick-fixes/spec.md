# Spec Delta

## ADDED Requirements

### Requirement: List, dictionary and repeated arguments of Create Keyword

When Create Keyword turns the arguments of the call into placeholders, a list expansion `@{…}` SHALL become `@{args}`, which also takes the positional arguments after it, and a dictionary expansion `&{…}` SHALL become `&{kwargs}` at the end. A name that the call gives more than once SHALL become one placeholder.

#### Scenario: List, dictionary and a repeated name
- **WHEN** the action for `Unknown Kw    a    @{LIST}    b=1    b=2    &{DICT}` is resolved
- **THEN** the created keyword has the line `[Arguments]    ${arg1}    @{args}    ${b}    &{kwargs}`

### Requirement: What Create local variable writes

For a `VariableNotFound` diagnostic in the body of a test or keyword, the quick fix "Create local variable" SHALL create the variable in the kind the code uses it: a scalar with the value `value`, a list `@{…}` with the item `value`, a dictionary `&{…}` with the item `key=value`. From Robot Framework 7.0 on it SHALL write `VAR`, before 7.0 `Set Variable`, `Create List` or `Create Dictionary`. Afterwards the value SHALL be selected.

#### Scenario: Scalar on Robot Framework 7.0 and newer
- **WHEN** the step `    Log    ${MISSING}` has the diagnostic and the action is resolved, on Robot Framework 7.0 or newer
- **THEN** the line `    VAR    ${MISSING}    value` is inserted before the step, and `value` is selected

#### Scenario: List before Robot Framework 7.0
- **WHEN** the step `    Log Many    @{ITEMS}` has the diagnostic and the action is resolved, on Robot Framework 6.1 or older
- **THEN** the line `    @{ITEMS}    Create List    value` is inserted before the step

#### Scenario: Dictionary on Robot Framework 7.0 and newer
- **WHEN** the step `    Log Many    &{OPTIONS}` has the diagnostic and the action is resolved, on Robot Framework 7.0 or newer
- **THEN** the line `    VAR    &{OPTIONS}    key=value` is inserted before the step, and `key=value` is selected

### Requirement: Where Create local variable writes

The variable SHALL be created on a line of its own before the statement that uses it, with that statement's indentation. When an `ELSE IF` or `EXCEPT` header uses it, the variable SHALL be created before the whole IF or TRY block, with the block's indentation. Create local variable SHALL NOT be offered for a default value in `[Arguments]` or a value in `[Tags]` or `[Timeout]`, which Robot Framework evaluates before the body runs.

#### Scenario: ELSE IF
- **WHEN** `ELSE IF    ${M}` in an IF block that starts with `    IF    ${TRUE}` has the diagnostic and the action is resolved
- **THEN** the variable is created on a new line directly before `    IF    ${TRUE}`

#### Scenario: EXCEPT
- **WHEN** `EXCEPT    ${M}` in a TRY block has the diagnostic and the action is resolved
- **THEN** the variable is created on a new line directly before the `TRY` line

#### Scenario: Default value of an argument
- **WHEN** a keyword has `[Arguments]    ${a}=${M}` and `${M}` has the diagnostic
- **THEN** "Create local variable" is not offered

#### Scenario: Tags of a test
- **WHEN** a test has `[Tags]    ${M}` and `${M}` has the diagnostic
- **THEN** "Create local variable" is not offered, and "Create suite variable" is

### Requirement: What Create suite variable writes

The quick fix "Create suite variable" SHALL write the variable in the kind the code uses it, `${…}    value`, `@{…}    value` or `&{…}    key=value`, into the Variables section: before the line of the variable when the diagnostic is in that section, otherwise after its last statement. Without a Variables section, a new one SHALL follow the settings section, or else come directly before the first section, after a `Language:` line. Afterwards exactly the value on the new line SHALL be selected.

#### Scenario: New Variables section after the settings
- **WHEN** a file has a settings section but no Variables section, `${NEW}` has the diagnostic, and the action is resolved
- **THEN** a new Variables section with the line `${NEW}    value` follows the settings section, and exactly `value` on that line is selected

#### Scenario: List
- **WHEN** `@{ITEMS}` has the diagnostic and the action is resolved
- **THEN** the Variables section gets the line `@{ITEMS}    value`

### Requirement: Where Add argument writes

For a `VariableNotFound` diagnostic in a keyword, the quick fix "Add argument" SHALL add `${name}=` to its `[Arguments]`: after the last argument, but before a free named argument `&{…}` and before the first argument whose default value uses the variable. Without `[Arguments]`, it SHALL insert an `[Arguments]` line before the first statement after the name and the documentation. Afterwards the cursor SHALL stand after the `=`.

#### Scenario: Free named arguments
- **WHEN** a keyword has `[Arguments]    ${a}    &{kw}`, the step `Log    ${M}` has the diagnostic, and the action is resolved
- **THEN** the line becomes `[Arguments]    ${a}    ${M}=    &{kw}`

#### Scenario: Default value that uses the variable
- **WHEN** a keyword has `[Arguments]    ${a}=${M}`, `${M}` has the diagnostic, and the action is resolved
- **THEN** the line becomes `[Arguments]    ${M}=    ${a}=${M}`

### Requirement: Language of new sections

A section header that Create Keyword, Extract Keyword or Create suite variable writes SHALL be in the language of the file, from Robot Framework 6.0 on: the language its `Language:` line names, otherwise the first language other than English that the workspace configures, otherwise English.

#### Scenario: Keyword section of a German file
- **WHEN** a file starts with `Language: German`, has no keyword section, and Create Keyword is resolved, on Robot Framework 6.0 or newer
- **THEN** the new section header is `*** Schlüsselwörter ***`

#### Scenario: Variables section of a German file without settings
- **WHEN** a file starts with `Language: German`, has neither a settings nor a Variables section, and Create suite variable is resolved, on Robot Framework 6.0 or newer
- **THEN** the new section `*** Variablen ***` comes after the `Language: German` line and before the first section, and Robot Framework still reads the file as German

### Requirement: Code action ranges in UTF-16

The ranges that code actions send to the editor, of their edits, of the range the editor selects afterwards and of the diagnostics they name, SHALL be in UTF-16 code units, as the editor sends ranges and as rename returns them.

#### Scenario: Line with a character outside the BMP
- **WHEN** a keyword has `[Arguments]    ${🤖}`, the step `Log    🤖 ${missing}` has the diagnostic, and "Add argument" is requested and resolved through the language server protocol
- **THEN** the edit inserts `    ${missing}=` at UTF-16 column 24 of the `[Arguments]` line, directly after `${🤖}`, the cursor goes to UTF-16 column 39, and the action names the diagnostic with the range the editor sent
