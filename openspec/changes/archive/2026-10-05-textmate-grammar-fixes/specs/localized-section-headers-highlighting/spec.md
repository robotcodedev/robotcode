# Spec Delta: localized-section-headers-highlighting

## MODIFIED Requirements

### Requirement: All accepted section header translations are highlighted

The TextMate grammars SHALL recognise the section headers of every built-in Robot Framework language in every spelling that a supported Robot Framework version accepts, including deprecated spellings that Robot Framework still accepts and spellings that only older supported versions accept, so that a suite using them is highlighted like an English suite. Adding a translation SHALL NOT remove a still-accepted one.

#### Scenario: Deprecated French test-cases header
- **WHEN** a file contains `*** Unités de test ***` with `language: fr`
- **THEN** the line is highlighted as a test-cases section header

#### Scenario: New French test-cases header
- **WHEN** a file contains `*** Cas de test ***` with `language: fr`
- **THEN** the line is highlighted as a test-cases section header

#### Scenario: Arabic section headers
- **WHEN** a file contains the Arabic settings, variables, test-cases, tasks, keywords or comments header with `language: ar`
- **THEN** the line is highlighted as the corresponding section header

#### Scenario: Dutch keywords header of older versions
- **WHEN** a file contains `*** Sleutelwoorden ***`, which Robot Framework 6.0 to 7.0 accept with `language: nl`
- **THEN** the line is highlighted as a keywords section header and the keywords below it are highlighted as keywords

### Requirement: Editor and REPL grammars agree on section headers

The REPL grammar SHALL be generated from the same template as the editor grammar, so that its section-header patterns accept the same header spellings as the editor grammar.

#### Scenario: REPL grammar after a header change
- **WHEN** a header spelling is added to the editor grammar
- **THEN** the REPL grammar recognises the same spelling
