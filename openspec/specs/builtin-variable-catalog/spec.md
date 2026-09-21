# Spec: builtin-variable-catalog

## Purpose

Defines that the set of built-in variables RobotCode treats as always defined follows the installed Robot Framework version, so that variables Robot Framework provides produce no false "variable not found" diagnostics and are offered in completion.

## Requirements

### Requirement: Test metadata variable is known on RF 7.5

On Robot Framework ≥ 7.5 RobotCode SHALL treat `TEST_METADATA` as a built-in variable in both its scalar and dictionary spelling (`${TEST_METADATA}`, `&{TEST_METADATA}`): using it SHALL NOT produce a "variable not found" diagnostic and it SHALL be offered in variable completion. On older versions it SHALL NOT be treated as built-in.

#### Scenario: Test metadata variable on RF 7.5
- **WHEN** a test contains `[Metadata]    Issue    4409` and a step `Log    ${TEST_METADATA}` and the file is analyzed on RF 7.5
- **THEN** no diagnostic is reported for `${TEST_METADATA}`
- **AND** no diagnostic is reported for the `[Metadata]` setting

#### Scenario: Completion on RF 7.5
- **WHEN** variable completion is requested inside a test body on RF 7.5
- **THEN** `${TEST_METADATA}` is among the offered built-in variables

#### Scenario: Test metadata variable on RF 7.4
- **WHEN** the same file is analyzed on RF 7.4
- **THEN** `${TEST_METADATA}` is reported as not found
- **AND** `[Metadata]` is reported with Robot Framework's own error for that version (its message starts with `Setting 'Metadata' is not allowed`)

### Requirement: Test-level Metadata produces no false diagnostics

On Robot Framework ≥ 7.5 a `[Metadata]` setting inside a test or task SHALL be accepted without diagnostics and SHALL be highlighted as a setting, like the suite-level `Metadata` setting. Displaying test metadata anywhere is not part of this capability.

#### Scenario: Semantic tokens for test-level Metadata
- **WHEN** a test contains `[Metadata]    Author    me` on RF 7.5
- **THEN** `[Metadata]` is highlighted as a setting name and the file has no diagnostics
