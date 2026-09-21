# Spec: localized-section-headers-highlighting

## Purpose

Guarantees that syntax highlighting recognises every section header spelling Robot Framework accepts in its built-in languages, including translations Robot Framework has deprecated but still accepts, in both the editor grammar and the REPL grammar.

## Requirements

### Requirement: All accepted section header translations are highlighted

The TextMate grammars SHALL recognise the section headers of every built-in Robot Framework language, including deprecated spellings that Robot Framework still accepts, so that a suite using them is highlighted like an English suite. Adding a translation SHALL NOT remove a still-accepted one.

#### Scenario: Deprecated French test-cases header
- **WHEN** a file contains `*** Unités de test ***` with `language: fr`
- **THEN** the line is highlighted as a test-cases section header

#### Scenario: New French test-cases header
- **WHEN** a file contains `*** Cas de test ***` with `language: fr`
- **THEN** the line is highlighted as a test-cases section header

#### Scenario: Arabic section headers
- **WHEN** a file contains the Arabic settings, variables, test-cases, tasks, keywords or comments header with `language: ar`
- **THEN** the line is highlighted as the corresponding section header

### Requirement: Editor and REPL grammars agree on section headers

The section-header patterns of the REPL grammar SHALL accept the same header spellings as the editor grammar.

#### Scenario: REPL grammar after a header change
- **WHEN** a header spelling is added to the editor grammar
- **THEN** the REPL grammar recognises the same spelling
