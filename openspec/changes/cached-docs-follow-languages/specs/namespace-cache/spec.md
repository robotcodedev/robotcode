## ADDED Requirements

### Requirement: A file read with other language settings is read again

RobotCode SHALL NOT use what the analysis cache keeps of a Robot Framework file, its keywords, variables and imports, when the language settings are not the same as when the file was read. The language settings are `languages` in robot.toml and the setting `robotcode.robot.languages`. RobotCode SHALL read the file again with the current language settings.

#### Scenario: Language added between two runs

- **WHEN** `keywords.resource` defines `Mein Keyword` under the German section header `*** Schlüsselwörter ***`, a suite imports it and calls `Mein Keyword`, `robotcode analyze code` runs without language settings, and `languages = ["de"]` is added to robot.toml before the next run
- **THEN** the next run reports neither `keywords.resource` as empty nor `Mein Keyword` as not found

#### Scenario: Language removed between two runs

- **WHEN** the same project is analyzed with `languages = ["de"]` in robot.toml, and the setting is removed before the next run
- **THEN** the next run reports `Mein Keyword` as not found in the suite, as a run with an empty cache does
