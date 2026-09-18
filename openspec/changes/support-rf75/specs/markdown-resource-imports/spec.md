# Spec Delta

## Purpose

Defines how resource imports of Markdown files are treated on Robot Framework ≥ 7.5, where `Resource    file.md` is valid: they are accepted and offered like reStructuredText resources are today, and are kept away from Libdoc, which rejects them.

## ADDED Requirements

### Requirement: Markdown resource imports are accepted on RF 7.5

On Robot Framework ≥ 7.5 a `Resource` import whose file ends with `.md` or `.markdown` (including `.robot.md`) SHALL be accepted: no "invalid resource file extension" diagnostic SHALL be reported and the file SHALL be loaded as a resource in the same way a `.rst` resource is loaded today. On older versions such imports SHALL be rejected as before. Extracting the Robot Framework code blocks from Markdown or reStructuredText resources is not part of this capability.

#### Scenario: Markdown resource on RF 7.5
- **WHEN** a suite contains `Resource    keywords.md` and is analyzed on RF 7.5
- **THEN** no invalid-extension diagnostic is reported for the import

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
