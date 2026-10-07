# Spec Delta

## MODIFIED Requirements

### Requirement: Tags section without an empty row is reported

On Robot Framework ≥ 7.5, a `Tags:` section in the `[Documentation]` of a keyword in a `.resource` file or in the `*** Keywords ***` section of a `.robot` file SHALL produce a warning with the Deprecated tag on the `Tags:` line, with the message Robot Framework prints ("Invalid documentation in '<keyword>': Not having an empty row before 'Tags:' is deprecated."), whenever Robot Framework itself warns about that documentation.

#### Scenario: Legacy layout
- **WHEN** a keyword's `[Documentation]` in a `.resource` file is `Does something.` followed by a continuation row `Tags: a, b` without an empty row between them, on RF 7.5
- **THEN** a warning with the Deprecated tag is reported on the `Tags: a, b` row

#### Scenario: Keyword in a suite file
- **WHEN** the same keyword is in the `*** Keywords ***` section of a `.robot` file, on RF 7.5
- **THEN** the same warning is reported

#### Scenario: Correct layout
- **WHEN** the documentation has an empty continuation row before `Tags: a, b`
- **THEN** no diagnostic is reported

#### Scenario: Tags on the first line
- **WHEN** the documentation is `[Documentation]    Tags: a, b`
- **THEN** no diagnostic is reported

#### Scenario: Tags after an Args section
- **WHEN** the documentation has an `Args:` section with an indented entry and `Tags: a` follows directly on the next row
- **THEN** no diagnostic is reported, as Robot Framework does not warn

#### Scenario: Prose line that looks like a header
- **WHEN** the documentation is `We use` followed by a continuation row `tags: for grouping`
- **THEN** the warning is reported on that row, as Robot Framework warns about it

#### Scenario: Older Robot Framework
- **WHEN** the legacy layout is analyzed on RF 7.4
- **THEN** no diagnostic is reported

#### Scenario: Suppressed
- **WHEN** the `Tags:` row carries `# robotcode: ignore[TagsWithoutEmptyRow]`
- **THEN** no diagnostic is reported for it

## ADDED Requirements

### Requirement: Where a Tags section may start

Robot Framework warns, and the warning SHALL be produced, when the `Tags:` header (case-insensitive, `Tags:` or `Tags::`, optional `*`/`_` emphasis) comes at a place where no documentation section may start. A section may start on the first line, after an empty line and inside a named section (`Args:`, `Returns:`, `Raises:` with their indented or empty lines).

#### Scenario: Header with two colons and emphasis
- **WHEN** on RF ≥ 7.5 a keyword's documentation has the line `**Tags::** a` directly after a line of text
- **THEN** the warning is produced on that line

### Requirement: Documentation that is not checked

Suite, test and resource-file documentation SHALL NOT be checked, and nothing SHALL be reported on Robot Framework ≤ 7.4.

#### Scenario: Suite documentation
- **WHEN** on RF ≥ 7.5 the `Documentation` setting of a suite file has a `Tags:` line directly after a line of text
- **THEN** nothing is reported

### Requirement: How the Tags section diagnostic is computed

The diagnostic is computed from the documentation's source rows while the file is analyzed; a `Tags:` header placed behind an escaped `\n` inside one row is not detected (Robot Framework reports it at run time). The diagnostic SHALL be identical whether the semantic-model analysis path is enabled or not, and SHALL be suppressible with the diagnostics modifiers.

#### Scenario: Escaped newline inside one row
- **WHEN** on RF ≥ 7.5 one `[Documentation]` row of a keyword contains `Does something.\nTags: a`
- **THEN** no warning is reported
