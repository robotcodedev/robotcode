# Spec Delta

## Purpose

How users suppress single diagnostics of RobotCode and findings of Robocop from the editor: quick fixes that write the matching comment for one line or for the whole file.

## ADDED Requirements

### Requirement: Disable a RobotCode diagnostic for one line

For each diagnostic with the source `robotcode` in the range of a code action request, the language server SHALL offer one quick fix "Disable '<code>' for this line" per diagnostic code. Applying it SHALL make RobotCode stop reporting that code on the line where the diagnostic starts, by an `ignore[<code>]` modifier on that line, and SHALL leave every other code of the line reported. Diagnostics of other sources SHALL NOT get this quick fix.

#### Scenario: A keyword that does not exist
- **WHEN** the user applies "Disable 'KeywordNotFound' for this line" at a call of a keyword that does not exist
- **THEN** the line ends with `# robotcode: ignore[KeywordNotFound]`
- **AND** the call is no longer reported, while a `VariableNotFound` on the same line still is

#### Scenario: Test discovery problems
- **WHEN** a diagnostic with the source `robotcode.discover` is in the range of the request
- **THEN** no "Disable … for this line" quick fix is offered for it

### Requirement: Modifier placement on a line with comments

When the line already has a comment, the quick fix for one line SHALL put the modifier where RobotCode reads it: into the line's `# robotcode:` comment if there is one, as an entry of its `ignore[...]` list or as an added `ignore[...]` segment, and otherwise as a new `# robotcode:` comment in front of the line's other comments.

#### Scenario: An ignore list on the line
- **WHEN** the line ends with `# robotcode: ignore[VariableNotFound]` and the user disables `KeywordNotFound` for this line
- **THEN** the comment reads `# robotcode: ignore[VariableNotFound,KeywordNotFound]`

#### Scenario: Another action on the line
- **WHEN** the line ends with `# robotcode: warn[VariableNotFound]` and the user disables `KeywordNotFound` for this line
- **THEN** the comment reads `# robotcode: warn[VariableNotFound] ignore[KeywordNotFound]`

#### Scenario: A plain comment on the line
- **WHEN** the line ends with `# check later` and the user disables `KeywordNotFound` for this line
- **THEN** the line ends with `# robotcode: ignore[KeywordNotFound]    # check later`
- **AND** the call is no longer reported

### Requirement: Disable a RobotCode diagnostic for a file

For each diagnostic with the source `robotcode` in the range of a code action request, the language server SHALL also offer "Disable '<code>' for this file". Applying it SHALL make RobotCode stop reporting that code anywhere in the file, by an `ignore[<code>]` modifier in a `# robotcode:` comment line at the top of the file, before its first section; an existing such line SHALL get the code instead of a second line.

#### Scenario: No modifier at the top yet
- **WHEN** a file starts with `*** Settings ***` and the user applies "Disable 'KeywordNotFound' for this file"
- **THEN** the file's first line is `# robotcode: ignore[KeywordNotFound]`
- **AND** no `KeywordNotFound` is reported in the file

#### Scenario: A modifier line at the top
- **WHEN** the file's first line is `# robotcode: ignore[VariableNotFound]` and the user disables `KeywordNotFound` for this file
- **THEN** that line reads `# robotcode: ignore[VariableNotFound,KeywordNotFound]` and no second modifier line is added

### Requirement: Disable a Robocop finding for one line

When Robocop 6.0 or newer is installed, the language server SHALL offer one quick fix "Disable '<code>' for this line" per code for the findings with the source `robocop` in the range of a code action request. Applying it SHALL make Robocop stop reporting the finding's rule on that line, by Robocop's disabler `# robocop: off=<rule name>` at the end of the line, or by adding the rule name to the `off=` list of such a comment on the line.

#### Scenario: An unused variable
- **WHEN** the user applies "Disable 'VAR02-unused-variable' for this line" at an assignment Robocop reports as unused
- **THEN** the line ends with `# robocop: off=unused-variable`
- **AND** Robocop no longer reports the assignment, while it still reports the same rule on other lines

#### Scenario: A Robocop disabler on the line
- **WHEN** the line already ends with `# robocop: off=<another rule>` and the user disables `VAR02-unused-variable` for this line
- **THEN** the comment reads `# robocop: off=<another rule>,unused-variable`

#### Scenario: Robocop older than 6.0
- **WHEN** a Robocop version older than 6.0 is installed
- **THEN** no "Disable …" quick fixes are offered for Robocop's findings

### Requirement: Disable a Robocop finding for a file

When Robocop 6.0 or newer is installed, the language server SHALL also offer "Disable '<code>' for this file" for the findings with the source `robocop`. Applying it SHALL make Robocop stop reporting the rule anywhere in the file, by a `# robocop: off=<rule name>` comment line at the top of the file, before its first section; an existing such line SHALL get the rule name in its `off=` list instead of a second line.

#### Scenario: Missing test documentation
- **WHEN** the user applies "Disable 'DOC02-missing-doc-test-case' for this file"
- **THEN** the file's first line is `# robocop: off=missing-doc-test-case`
- **AND** Robocop reports no missing test documentation in the file
