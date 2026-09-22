# Spec Delta

## Purpose

Defines the diagnostic and quick fix RobotCode provides for the layout of `Tags:` sections in keyword documentation that Robot Framework has deprecated — when it applies and how it can be suppressed.

## ADDED Requirements

### Requirement: Tags section without an empty row is reported

On Robot Framework ≥ 7.5, a `Tags:` section in the `[Documentation]` of a keyword in a resource or suite file that is not preceded by an empty row SHALL produce a warning with the Deprecated tag on the `Tags:` line, with the message Robot Framework uses ("Not having an empty row before 'Tags:' is deprecated.") and matching the rule Robot Framework applies (section header recognised case-insensitively, `Tags:` or `Tags::`, optional emphasis). A `Tags:` header that is the first line of the documentation or that follows an empty row SHALL NOT be reported. Suite, test and resource-file documentation SHALL NOT be checked, and nothing SHALL be reported on Robot Framework ≤ 7.4. The rule works on the documentation's source rows; a `Tags:` header placed behind an escaped `\n` inside one row is not detected (Robot Framework reports it at run time). The diagnostic SHALL be identical whether the semantic-model analysis path is enabled or not, and SHALL be suppressible with the diagnostics modifiers.

#### Scenario: Legacy layout
- **WHEN** a resource keyword's `[Documentation]` is `First line` followed by a continuation row `Tags: alpha, beta` without an empty row between them, on RF 7.5
- **THEN** a warning with the Deprecated tag is reported on the `Tags: alpha, beta` line

#### Scenario: Correct layout
- **WHEN** the documentation has an empty continuation row before `Tags: alpha, beta`
- **THEN** no diagnostic is reported

#### Scenario: Older Robot Framework
- **WHEN** the legacy layout is analyzed on RF 7.4
- **THEN** no diagnostic is reported

#### Scenario: Suppressed
- **WHEN** the `Tags:` row carries `# robotcode: ignore[TagsWithoutEmptyRow]`
- **THEN** no diagnostic is reported for it

### Requirement: Quick fix inserts the empty row

For the `Tags:`-layout diagnostic RobotCode SHALL offer a quick fix that inserts an empty continuation row (`...` with the same indentation as the `Tags:` row) before the `Tags:` line, after which the documentation value contains an empty line before the section.

#### Scenario: Insert empty row
- **WHEN** the quick fix is applied to a keyword whose `Tags:` row is `    ...    Tags: alpha, beta`
- **THEN** a row `    ...` is inserted before it
- **AND** re-analysis reports no `Tags:`-layout diagnostic
