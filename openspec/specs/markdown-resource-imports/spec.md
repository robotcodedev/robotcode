# Spec: markdown-resource-imports

## Purpose

Defines how resource imports of Markdown files are treated on Robot Framework ≥ 7.5, where `Resource    file.md` is valid: they are accepted and offered like reStructuredText resources are today, and are kept away from Libdoc, which rejects them.

## Requirements

### Requirement: Markdown resource imports are accepted on RF 7.5

On Robot Framework ≥ 7.5 a `Resource` import whose file ends with `.md` or `.markdown` (including `.robot.md`) SHALL be accepted without an "invalid resource file extension" diagnostic. On 7.5.1 or newer the file SHALL be loaded from its Robot Framework code blocks, as Robot Framework loads it, also when no Markdown format is active; on 7.5.0 it SHALL be loaded as before. On older versions such imports SHALL be rejected as before.

#### Scenario: Markdown resource on RF 7.5
- **WHEN** a suite contains `Resource    keywords.md` and is analyzed on RF 7.5
- **THEN** no invalid-extension diagnostic is reported for the import

#### Scenario: Keyword from a Markdown resource
- **WHEN** a `.robot` suite imports `keywords.md`, whose `robotframework` code block defines `Greet`, and calls `Greet`, on Robot Framework 7.5.1 and without `extensions` in the robot.toml
- **THEN** the call is resolved without diagnostics, and go-to-definition on `Greet` opens `keywords.md` at the line of `Greet`

#### Scenario: Prose of a Markdown resource
- **WHEN** `keywords.md` of the previous scenario also has the prose line `Some notes` at column 1
- **THEN** completion of keywords in the suite does not offer `Some notes`

#### Scenario: Markdown resource on RF 7.4
- **WHEN** the same suite is analyzed on RF 7.4
- **THEN** the import is reported as an invalid resource file extension, as before

### Requirement: Markdown resources appear in import completion

On Robot Framework ≥ 7.5 completion of a `Resource` import path SHALL list `.md` and `.markdown` files alongside the other resource file extensions.

#### Scenario: Completion of a resource path
- **WHEN** completion is requested after `Resource    ` in a directory containing `keywords.md` and `other.resource` on RF 7.5
- **THEN** both files are offered

### Requirement: Markdown resources are not passed to Libdoc HTML generation

Requesting Libdoc HTML documentation for a Markdown resource SHALL produce a readable error message rather than an unhandled failure, because Robot Framework's Libdoc does not accept Markdown resource files.

#### Scenario: Documentation web view for a Markdown resource
- **WHEN** the HTML documentation of `keywords.md` is requested on RF 7.5
- **THEN** the documentation web view shows a message that Libdoc does not support Markdown resources
