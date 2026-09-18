# Spec Delta

<!-- Modifies a requirement introduced by the change support-rf75 (archive support-rf75 first). -->

## MODIFIED Requirements

### Requirement: Markdown resource imports are accepted on RF 7.5

On Robot Framework ≥ 7.5 a `Resource` import whose file ends with `.md` or `.markdown` (including `.robot.md`) SHALL be accepted: no "invalid resource file extension" diagnostic SHALL be reported and the file SHALL be loaded from the Robot Framework code blocks it contains, so that its keywords and variables are available to the importing file. On older versions such imports SHALL be rejected as before.

#### Scenario: Markdown resource on RF 7.5
- **WHEN** a suite contains `Resource    keywords.md` and is analyzed on RF 7.5
- **THEN** no invalid-extension diagnostic is reported for the import

#### Scenario: Keyword from a Markdown resource
- **WHEN** a suite imports `keywords.md` whose `robotframework` fence defines `Greet` and calls `Greet`, on RF 7.5
- **THEN** the call resolves without diagnostics and completion offers `Greet`

#### Scenario: Markdown resource on RF 7.4
- **WHEN** the same suite is analyzed on RF 7.4
- **THEN** the import is reported as an invalid resource file extension, as before
