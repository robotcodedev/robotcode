# Spec Delta

## Purpose

Defines what completing an environment variable name inside `%{…}` changes in the text, so that the `=default` part of `%{NAME=default}` survives when a name is chosen from the completion list.

## ADDED Requirements

### Requirement: Completing an environment variable name keeps the default

When completion is requested inside `%{…}` whose content contains a `=`, with the cursor between `%{` and the first `=` (the position directly before the `=` included), the language server SHALL offer the environment variable names with an edit range that ends no later than that `=`. Accepting an item SHALL leave the `=` and everything after it up to the closing brace unchanged. In the scenarios `|` marks the cursor and `ENV_VAR` is an environment variable known to the language server.

#### Scenario: Empty default
- **WHEN** completion is requested at `Log    %{NO|PE_EMPTY_DEFAULT=}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    %{ENV_VAR=}`

#### Scenario: Non-empty default
- **WHEN** completion is requested at `Log    %{NO|PE=abc}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    %{ENV_VAR=abc}`

#### Scenario: Cursor at the start of the name
- **WHEN** completion is requested at `Log    %{|NOPE=abc}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    %{ENV_VAR=abc}`

#### Scenario: Cursor directly before the equals sign
- **WHEN** completion is requested at `Log    %{NOPE|=abc}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    %{ENV_VAR=abc}`

#### Scenario: Several variables in one argument
- **WHEN** completion is requested at `Log    x%{NO|PE=abc}y%{OTHER}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    x%{ENV_VAR=abc}y%{OTHER}`

### Requirement: The default does not change the completion range

The edit range SHALL be the one the same cursor position gets in `%{NAME}`, where `NAME` is the text between `%{` and the first `=`; the default SHALL NOT influence it, whether it is empty, contains `+`, `-`, `*`, `/` or variables, or the closing brace is still missing. In the scenarios `|` marks the cursor and `ENV_VAR` is an environment variable known to the language server.

#### Scenario: Default with a path
- **WHEN** completion is requested at `Log    %{NO|PE=/tmp}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    %{ENV_VAR=/tmp}`

#### Scenario: Default that contains a variable
- **WHEN** completion is requested at `Log    %{NE|_UNSET=${S}}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    %{ENV_VAR=${S}}`

#### Scenario: Closing brace still missing
- **WHEN** completion is requested at `Log    %{NO|PE=` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    %{ENV_VAR=`

#### Scenario: Variable without a default
- **WHEN** completion is requested at `Log    %{NO|PE}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    %{ENV_VAR}`, as before this change

#### Scenario: Default of a later variable in the same argument
- **WHEN** completion is requested at `Log    x%{NO|PE}y%{B=c}` and the item `ENV_VAR` is accepted
- **THEN** the line reads `Log    x%{ENV_VAR}y%{B=c}`, as before this change

### Requirement: No environment variable names in the default

When the cursor is after the first `=` inside `%{…}`, the language server SHALL NOT offer environment variable names for that variable. Completion for a variable written inside the default SHALL work as for any other variable.

#### Scenario: Cursor inside the default
- **WHEN** completion is requested at `Log    %{NOPE=ab|c}`
- **THEN** no environment variable name is offered

#### Scenario: Cursor directly after the equals sign
- **WHEN** completion is requested at `Log    %{NOPE=|abc}`
- **THEN** no environment variable name is offered

#### Scenario: Cursor directly after the equals sign of an empty default
- **WHEN** completion is requested at `Log    %{NOPE=|}`
- **THEN** no environment variable name is offered

#### Scenario: Cursor at the end of the default
- **WHEN** completion is requested at `Log    %{NOPE=abc|}`
- **THEN** no environment variable name is offered

#### Scenario: Cursor in the default of a variable without closing brace
- **WHEN** completion is requested at `Log    %{NOPE=|`
- **THEN** no environment variable name is offered

#### Scenario: Variable inside the default
- **WHEN** a suite defines `${S}` and completion is requested at `Log    %{NE_UNSET=${|S}}`
- **THEN** variable items are offered whose edit range covers only the `S` between `${` and `}`
