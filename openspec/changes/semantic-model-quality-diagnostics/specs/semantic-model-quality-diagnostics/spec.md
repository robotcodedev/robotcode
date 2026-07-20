# Spec: semantic-model-quality-diagnostics

## ADDED Requirements

### Requirement: Extended dead-code diagnostics from the model

RobotCode SHALL offer model-derived dead-code diagnostics — unused loop variables, unused `EXCEPT AS` variables, empty control-flow blocks, unreachable code after `RETURN`/`BREAK`/`CONTINUE`, and shadowed `VAR` definitions — each independently configurable (enable + severity) and off unless enabled. Rules SHALL be conservative: a case is flagged only when the model is certain, to avoid false positives on dynamic patterns.

#### Scenario: Unused loop variable

- **WHEN** a FOR loop declares `${i}` that is never referenced in the loop body and the check is enabled
- **THEN** a diagnostic marks `${i}` as unused

#### Scenario: Unreachable code after RETURN

- **WHEN** a statement follows a `RETURN` within the same block and the check is enabled
- **THEN** that statement is reported as unreachable

#### Scenario: Disabled by default does not change existing output

- **WHEN** a project has not enabled the extended checks
- **THEN** its diagnostic output is identical to before this change

### Requirement: Per-definition complexity metrics

RobotCode SHALL compute cyclomatic complexity and nesting depth per keyword/test `DefinitionBlock` from control-flow statement subclasses and Run-Keyword conditionals, and surface complexity as a code lens, with an optional threshold diagnostic behind a setting.

#### Scenario: Complexity code lens

- **WHEN** a keyword contains two `IF` branches and a `FOR` loop
- **THEN** a code lens reports the keyword's cyclomatic complexity

#### Scenario: Threshold diagnostic

- **WHEN** a keyword's complexity exceeds the configured threshold and the threshold diagnostic is enabled
- **THEN** a diagnostic reports the keyword as too complex

### Requirement: Enhanced argument validation

RobotCode SHALL validate keyword calls against `stmt.keyword_doc.arguments_spec` — too many positional arguments, unknown named arguments, missing required arguments — for cases the analyzer does not already report, without double-reporting cases it does.

#### Scenario: Unknown named argument

- **WHEN** a resolved keyword call passes `notaparam=1` and the keyword has no such parameter
- **THEN** a diagnostic reports the unknown named argument, and the same position is not reported twice
