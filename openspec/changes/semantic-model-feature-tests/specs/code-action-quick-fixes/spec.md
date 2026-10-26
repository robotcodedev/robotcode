# Spec: code-action-quick-fixes

## Purpose

Quick fixes offer edits for the diagnostics in the requested range, such as creating a keyword that is not found. The rules hold for the semantic-model analysis path, the default from `semantic-model-switchover` on.

## ADDED Requirements

### Requirement: Create Keyword is offered for keywords that are not found

When the request names no kinds or names `quickfix`, the quick fix "Create Keyword `<name>`" of kind `quickfix` SHALL be offered as preferred action for every `KeywordNotFound` diagnostic of the analysis; its edit SHALL be computed when the action is resolved. It SHALL be offered for steps, also with an assignment, in blocks and in the branches of an inline IF, for setup and teardown settings, for template keywords and for the inner keyword of a Run Keyword variant.

#### Scenario: Branch of an inline IF
- **WHEN** quick fixes are requested on `Unknown In Inline If` in `IF    ${TRUE}    Unknown In Inline If    x`
- **THEN** "Create Keyword `Unknown In Inline If`" is offered

#### Scenario: Template keyword
- **WHEN** quick fixes are requested on `Unknown Template` in `[Template]    Unknown Template`
- **THEN** "Create Keyword `Unknown Template`" is offered

#### Scenario: Inner keyword of Run Keyword
- **WHEN** quick fixes are requested on `Unknown Inner` in `Run Keyword    Unknown Inner    q`
- **THEN** "Create Keyword `Unknown Inner`" is offered, and no action is offered for `Run Keyword`

### Requirement: Name of the created keyword

The name SHALL be the called name without a BDD prefix, also a localized one (Robot Framework 6.0 and newer), and without a prefix that names an import. A prefix that names no import SHALL stay part of the name.

#### Scenario: BDD prefix
- **WHEN** quick fixes are requested on `Given Unknown Bdd Thing    x`
- **THEN** "Create Keyword `Unknown Bdd Thing`" is offered

#### Scenario: Prefix that names no import
- **WHEN** quick fixes are requested on `UnknownLib.Unknown Dotted`
- **THEN** "Create Keyword `UnknownLib.Unknown Dotted`" is offered

### Requirement: Where the keyword is created

When the prefix of the call names a library, the action SHALL be disabled with the reason "Keyword is from a library"; when it names a resource file, the keyword SHALL be created in that file; otherwise in the current file. A BDD prefix SHALL be removed before the prefix is determined.

#### Scenario: BDD prefix and resource prefix
- **WHEN** `res.resource` is imported and quick fixes are requested on `Given res.Unknown Bdd Res`
- **THEN** the resolved action creates `Unknown Bdd Res` in `res.resource`

#### Scenario: BDD prefix and library prefix
- **WHEN** quick fixes are requested on `When BuiltIn.Unknown Bdd Lib`
- **THEN** the action is disabled with the reason "Keyword is from a library"

### Requirement: Arguments of the created keyword

The arguments of the call SHALL become placeholders in the `[Arguments]` line: a `name=value` whose name is literal becomes `${name}`, a positional argument or a `name=value` whose name contains a variable `${argN}` with N its position. Without arguments there SHALL be no `[Arguments]` line. For the inner keyword of a Run Keyword variant only its own arguments SHALL count, for a template keyword the arguments of the first data row that uses it.

#### Scenario: Positional and named argument
- **WHEN** the action for `Unknown Args    a    b=1` is resolved
- **THEN** the created keyword has the line `[Arguments]    ${arg1}    ${b}`

#### Scenario: Inner keyword with a condition before it
- **WHEN** the action for `Unknown Rki Inner` in `Run Keyword If    ${TRUE}    Unknown Rki Inner    q` is resolved
- **THEN** the created keyword has the line `[Arguments]    ${arg1}`

#### Scenario: Template keyword
- **WHEN** a test has `[Template]    Unknown Template` and the data row `1    2`, and the action is resolved
- **THEN** the created keyword has the line `[Arguments]    ${arg1}    ${arg2}`

### Requirement: Text and place of the created keyword

The created keyword SHALL consist of its name, the `[Arguments]` line, the comment `# TODO: implement keyword "<name>".` and `Fail    Not Implemented`, indented and separated by four spaces. It SHALL be inserted after the last statement of the last keyword section with two empty lines before it, or in a new keyword section at the end of the file. Afterwards `Fail    Not Implemented` SHALL be selected.

#### Scenario: File with a keyword section
- **WHEN** the action for `Unknown Plain` is resolved in a file whose keyword section ends with the keyword `Existing` and its step `No Operation`
- **THEN** two empty lines and the lines `Unknown Plain`, `    # TODO: implement keyword "Unknown Plain".` and `    Fail    Not Implemented` are inserted after `No Operation`, and `Fail    Not Implemented` is selected

### Requirement: Differences from the legacy path

Where the semantic-model analysis path and the legacy path differ, the semantic-model path SHALL create the keyword given in the scenarios of this requirement; the legacy path keeps its own until `semantic-model-cleanup` removes it.

#### Scenario: Arguments of an inner keyword
- **WHEN** the action for `Unknown Rki Inner` in `Run Keyword If    ${TRUE}    Unknown Rki Inner    q` is resolved
- **THEN** the created keyword has the line `[Arguments]    ${arg1}`, where the legacy path also counts the condition and the keyword name

#### Scenario: Arguments of a template keyword
- **WHEN** a test has `[Template]    Unknown Template` and the data row `1    2`, and the action is resolved
- **THEN** the created keyword has the line `[Arguments]    ${arg1}    ${arg2}`, where the legacy path creates no `[Arguments]` line
