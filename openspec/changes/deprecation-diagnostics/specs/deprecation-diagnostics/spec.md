# Spec Delta

## Purpose

Defines the diagnostics, quick fixes and completion behaviour RobotCode provides for spellings Robot Framework has deprecated — translated section headers and settings, and the layout of `Tags:` sections in keyword documentation — including when they apply and how they can be suppressed.

## ADDED Requirements

### Requirement: Deprecated translated headers and settings are reported

On Robot Framework ≥ 7.5, a section header or a setting (suite settings such as `Testin Tagit`, local settings such as `[Tagit]`) written in a spelling that the active languages declare as deprecated SHALL produce an information-level diagnostic with the Deprecated tag on the header or setting token, naming the replacement and the version ("… is deprecated since Robot Framework 7.5. Use 'Tunnisteet' instead."). Deprecations declared by custom language files SHALL be reported the same way. No diagnostic SHALL be produced when Robot Framework itself already reports an error for the token, and nothing SHALL be reported on Robot Framework ≤ 7.4. The diagnostic SHALL be identical whether the semantic-model analysis path is enabled or not, and SHALL be suppressible with the diagnostics modifiers.

#### Scenario: Deprecated French header
- **WHEN** a file with `Language: fr` contains `*** Unités de test ***` and is analyzed on RF 7.5
- **THEN** an information diagnostic with the Deprecated tag covers the header and names `Cas de test`
- **AND** the file has no other diagnostics for that line

#### Scenario: Deprecated Finnish settings
- **WHEN** a file with `Language: fi` contains `Testin Tagit` in the settings section and `[Tagit]` in a test on RF 7.5
- **THEN** each of them gets the diagnostic naming `Testin Tunnisteet` and `Tunnisteet` respectively

#### Scenario: Older Robot Framework
- **WHEN** the same files are analyzed on RF 7.4
- **THEN** no deprecation diagnostic is reported

#### Scenario: Suppressed
- **WHEN** the header line carries `# robotcode: ignore[DeprecatedTranslation]`
- **THEN** no diagnostic is reported for it

### Requirement: Quick fix replaces a deprecated term

For a deprecated-translation diagnostic RobotCode SHALL offer a quick fix "Replace with '<new term>'" that replaces only the term, keeping the header decoration (`*** … ***`, `*…*`) and the brackets of local settings.

#### Scenario: Header replacement keeps decoration
- **WHEN** the quick fix is applied to `*** Unités de test ***`
- **THEN** the line becomes `*** Cas de test ***`

#### Scenario: Local setting replacement
- **WHEN** the quick fix is applied to `[Tagit]`
- **THEN** it becomes `[Tunnisteet]`

### Requirement: Completion marks deprecated settings

On Robot Framework ≥ 7.5 completion items for deprecated setting spellings SHALL carry the Deprecated completion tag and SHALL sort after the current spellings; the current spellings SHALL be offered unmarked. Deprecated header spellings SHALL NOT be offered.

#### Scenario: Setting completion in a Finnish file
- **WHEN** settings completion is requested in a test with `Language: fi` on RF 7.5
- **THEN** `[Tunnisteet]` is offered without a deprecation tag
- **AND** `[Tagit]` is offered with the Deprecated tag and sorted after it

### Requirement: Tags section without an empty row is reported

On Robot Framework ≥ 7.5, a `Tags:` section in the `[Documentation]` of a keyword in a resource or suite file that is not preceded by an empty row SHALL produce a warning with the Deprecated tag on the `Tags:` line, matching the rule Robot Framework applies (section header recognised case-insensitively, `Tags:` or `Tags::`, optional emphasis). A `Tags:` header that is the first line of the documentation or that follows an empty row SHALL NOT be reported. Suite, test and resource-file documentation SHALL NOT be checked. The rule works on the documentation's source rows; a `Tags:` header placed behind an escaped `\n` inside one row is not detected (Robot Framework reports it at run time).

#### Scenario: Legacy layout
- **WHEN** a resource keyword's `[Documentation]` is `First line` followed by a continuation row `Tags: alpha, beta` without an empty row between them, on RF 7.5
- **THEN** a warning with the Deprecated tag is reported on the `Tags: alpha, beta` line

#### Scenario: Correct layout
- **WHEN** the documentation has an empty continuation row before `Tags: alpha, beta`
- **THEN** no diagnostic is reported

### Requirement: Quick fix inserts the empty row

For the `Tags:`-layout diagnostic RobotCode SHALL offer a quick fix that inserts an empty continuation row (`...` with the same indentation as the `Tags:` row) before the `Tags:` line, after which the documentation value contains an empty line before the section.

#### Scenario: Insert empty row
- **WHEN** the quick fix is applied to a keyword whose `Tags:` row is `    ...    Tags: alpha, beta`
- **THEN** a row `    ...` is inserted before it
- **AND** re-analysis reports no `Tags:`-layout diagnostic
