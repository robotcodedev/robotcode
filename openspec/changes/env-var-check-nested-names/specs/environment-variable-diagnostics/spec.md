# Spec Delta

## Purpose

Defines when RobotCode reports that an environment variable (`%{...}`) used in a file is not set, for names written plainly and for names that contain other variables, on both analysis paths.

## ADDED Requirements

### Requirement: Environment variable names with nested variables are not checked as written

When the name of an environment variable reference without default (`%{...}` without `=`) contains a variable — `${...}`, `@{...}`, `&{...}`, `%{...}` or an inline Python expression `${{...}}`, but not an escaped `\${...}` — RobotCode SHALL NOT report `EnvironmentVariableNotFound` or `EnvironmentVariableNotReplaced` for that environment variable under its name as written in the source, on any Robot Framework version and on either analysis path.

#### Scenario: Name resolves to a set environment variable
- **WHEN** `${STAGE}` is `test` in the `*** Variables ***` section, the environment variable `APP_test` is set, and a test contains `Log    %{APP_${STAGE}}`
- **THEN** no diagnostic is reported

#### Scenario: Resolved value contains an equals sign
- **WHEN** `${KEY}` is `HOST=localhost` in the `*** Variables ***` section, `APP_HOST` is not set, and a test contains `Log    %{APP_${KEY}}`
- **THEN** no diagnostic is reported, as Robot Framework resolves the reference to its default `localhost`

#### Scenario: Name given by a set environment variable
- **WHEN** the environment variable `VAR_NAME` is set to `APP_test`, `APP_test` is set, and a test contains `Log    %{%{VAR_NAME}}`
- **THEN** no diagnostic is reported

### Requirement: Nested environment variable names without the semantic-model analysis path

With the semantic-model analysis path disabled, RobotCode SHALL NOT report any existence diagnostic for an environment variable reference without default whose name contains a variable. Whether the semantic-model analysis path reports an existence diagnostic under a name it resolves statically is not specified by this requirement.

#### Scenario: Name resolves to an unset environment variable, semantic-model analysis path disabled
- **WHEN** `${STAGE}` is `prod` in the `*** Variables ***` section, `APP_prod` is not set, a test contains `Log    %{APP_${STAGE}}`, and the semantic-model analysis path is disabled
- **THEN** no diagnostic is reported, although Robot Framework fails at run time with `Environment variable '%{APP_prod}' not found.`

#### Scenario: List, dictionary or inline Python in the name
- **WHEN** `@{LIST}` and `&{DICT}` are defined in the `*** Variables ***` section, no environment variable whose name starts with `APP_` is set, and a test contains `Log    %{APP_@{LIST}}`, `Log    %{APP_&{DICT}}` or `Log    %{APP_${{'X'}}}`
- **THEN** no `EnvironmentVariableNotFound` names the reference as written, and with the semantic-model analysis path disabled no `EnvironmentVariableNotFound` is reported for it

### Requirement: Variables nested in an environment variable name are analyzed

The variables nested in the name of an environment variable reference SHALL still be analyzed like any other variable reference: an undefined nested variable SHALL be reported as `VariableNotFound` (in documentation and metadata as the `VariableNotReplaced` hint), and a nested environment variable without default that is not set SHALL be reported as `EnvironmentVariableNotFound` (in documentation and metadata as the `EnvironmentVariableNotReplaced` hint) with its own name.

#### Scenario: Undefined variable in the name
- **WHEN** a test contains `Log    %{APP_${UNDEFINED}}` and `${UNDEFINED}` is not defined
- **THEN** exactly one diagnostic is reported for the argument: `VariableNotFound` with the message `Variable '${UNDEFINED}' not found.`, its range on `UNDEFINED`

#### Scenario: Name given by an unset environment variable
- **WHEN** `UNSET_NAME` is not set and a test contains `Log    %{%{UNSET_NAME}}`
- **THEN** exactly one diagnostic is reported for the argument: `EnvironmentVariableNotFound` with the message `Environment variable '%{UNSET_NAME}' not found.`, its range on `UNSET_NAME` of the inner `%{UNSET_NAME}`

#### Scenario: Undefined variable in the name inside documentation
- **WHEN** a test has `[Documentation]    doc %{APP_${UNDEFINED}}` and `${UNDEFINED}` is not defined
- **THEN** only the `VariableNotReplaced` hint `Variable '${UNDEFINED}' not replaced.` is reported for that row

### Requirement: Plain environment variable names keep their existence check

For an environment variable reference whose name contains neither a variable nor a backslash, RobotCode SHALL report as before this change: `%{NAME}` without default whose `NAME` is not set in the environment of the analyzing process SHALL be reported as the error `EnvironmentVariableNotFound` with the message `Environment variable '%{NAME}' not found.`. This SHALL hold on both analysis paths.

#### Scenario: Unset variable without default
- **WHEN** `APP_UNSET` is not set and a test contains `Log    %{APP_UNSET}`
- **THEN** the error `EnvironmentVariableNotFound` with the message `Environment variable '%{APP_UNSET}' not found.` is reported

### Requirement: Unset plain environment variables in documentation

In documentation and metadata, an environment variable reference without default whose name contains neither a variable nor a backslash, and whose `NAME` is not set, SHALL be reported as the hint `EnvironmentVariableNotReplaced` with `Environment variable '%{NAME}' not replaced.`, on both analysis paths.

#### Scenario: Unset variable in documentation
- **WHEN** `APP_UNSET` is not set and a test has `[Documentation]    doc %{APP_UNSET}`
- **THEN** the hint `EnvironmentVariableNotReplaced` with the message `Environment variable '%{APP_UNSET}' not replaced.` is reported

### Requirement: Plain environment variable names that are not reported

For an environment variable reference whose name contains neither a variable nor a backslash, `%{NAME=}` and `%{NAME=default}` SHALL NOT be reported, and `%{NAME}` whose `NAME` is set SHALL NOT be reported, on both analysis paths.

#### Scenario: Unset variable with a default
- **WHEN** `APP_UNSET` is not set and a test contains `Log    %{APP_UNSET=}` or `Log    %{APP_UNSET=abc}`
- **THEN** no diagnostic is reported

#### Scenario: Set variable
- **WHEN** `APP_test` is set and a test contains `Log    %{APP_test}`
- **THEN** no diagnostic is reported

### Requirement: Escaped variables in environment variable names

An escaped variable in the name of an environment variable reference (`\${...}`) is not a variable: such a name SHALL NOT be exempted from the existence check like a name that contains a variable, and when neither the name as written nor the name without the escaping backslash is set, `EnvironmentVariableNotFound` SHALL be reported for it. This SHALL hold on both analysis paths. Names with other backslash escapes, such as an escaped brace (`%{NAME_\{B}`), are not covered by this requirement.

#### Scenario: Escaped variable in the name
- **WHEN** a test contains `Log    %{APP_\${STAGE}}` and neither `APP_\${STAGE}` nor `APP_${STAGE}` is set
- **THEN** `EnvironmentVariableNotFound` is reported for it, as before this change
