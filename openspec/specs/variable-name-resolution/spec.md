# variable-name-resolution Specification

## Purpose

Defines which diagnostics RobotCode reports for variable names and references with nested variables that it resolves statically on Robot Framework 7.0 and newer: the existing hint for names it cannot resolve instead of an error or a name with unresolved text where the result depends on text the analyzer cannot resolve, the previous result otherwise.

## Requirements

### Requirement: Environment variable in a declared variable name

On Robot Framework 7.0 and newer, when the name of a variable declared in the `*** Variables ***` section, in a `VAR` statement or by an assignment contains an environment variable (`%{...}`), directly or through the value of another variable, RobotCode SHALL treat the name as not statically resolvable if that environment variable is not statically resolvable (requirement "Environment variables that are not statically resolvable"). On Robot Framework older than 7.0 nothing SHALL change.

#### Scenario: Name of the environment variable contains a variable
- **WHEN** `${X_%{NE_A_${S}}}    v` is declared in the `*** Variables ***` section with `${S}` = `suffix` and the environment variable `NE_A_suffix` set, on Robot Framework 7.5
- **THEN** the hint `VariableNameNotStaticallyResolvable` is reported on the name, `VariableNameNotResolvable` is not reported, and no variable is defined for the declaration

#### Scenario: Environment variable in the value of another variable
- **WHEN** `${A}    %{NE_A_${S}}` and `${V_${A}}    v` are declared
- **THEN** the hint `VariableNameNotStaticallyResolvable` is reported on `${V_${A}}` and no error says that `${A}` is not found

#### Scenario: Robot Framework older than 7.0
- **WHEN** `${X_%{NE_A_${S}}}    v` is analyzed on Robot Framework 6.1
- **THEN** neither `VariableNameNotStaticallyResolvable` nor `VariableNameNotResolvable` is reported, as before

### Requirement: Environment variables that are not statically resolvable

An environment variable (`%{...}`) SHALL count as not statically resolvable if the name of the environment variable (the text before the first `=` that is not part of a nested variable) contains a variable and the environment variable has no default or a default that contains a variable, or if the environment variable is not set and its default contains a variable. An escaped variable (`\${name}`) SHALL NOT count as a variable.

#### Scenario: Default of an unset environment variable contains a variable
- **WHEN** `${Y_%{NE_X=${S}}}    v` is declared with `${S}` = `suffix` and `NE_X` not set
- **THEN** the hint `VariableNameNotStaticallyResolvable` is reported on the name and no variable (in particular none named `${Y_${S}}`) is defined

#### Scenario: Escaped variable in the environment variable name
- **WHEN** `${E_%{NE_A_\${S}}}    v` is declared and neither `NE_A_\${S}` nor `NE_A_${S}` is set
- **THEN** the error `VariableNameNotResolvable` is reported, as before

### Requirement: Declarations whose name is not statically resolvable

For a declaration whose name is not statically resolvable, RobotCode SHALL report the hint `VariableNameNotStaticallyResolvable` on the name, SHALL NOT report the error `VariableNameNotResolvable` for it, and SHALL NOT define a variable for it. Variables nested in the environment variable SHALL keep their own diagnostics. The hint and the error of this requirement SHALL be reported identically whether the semantic-model analysis path is enabled or not.

#### Scenario: VAR statement and assignment
- **WHEN** a test contains `VAR    ${P_%{NE_A_${S}}}    p` and `${Q_%{NE_A_${S}}}=    Set Variable    q`
- **THEN** the hint `VariableNameNotStaticallyResolvable` is reported on both names and `VariableNameNotResolvable` on neither

#### Scenario: Undefined variable nested in the environment variable
- **WHEN** `${Z_%{NE_A_${UNDEF}}}    v` is declared and `${UNDEF}` is not defined
- **THEN** the hint `VariableNameNotStaticallyResolvable` is reported on the name and the error `VariableNotFound` on `${UNDEF}`

### Requirement: Statically resolvable environment variables in declared names

An environment variable whose name contains a variable and whose default contains no variable SHALL resolve to that default, whether or not the resolved environment variable is set. An environment variable whose name contains no variable SHALL be resolved as before: to its value when it is set, to its default when it is not set and the default contains no variable, and to the error `VariableNameNotResolvable` when it is not set and has no default.

#### Scenario: Name of the environment variable contains a variable, default without variables
- **WHEN** `${N_%{NE_${S}=fb}}    v` is declared with `${S}` = `suffix` and `NE_suffix` not set, and a test contains `Log    ${N_fb}`
- **THEN** the variable `${N_fb}` is defined, `VariableNameNotStaticallyResolvable` is not reported for the name and `VariableNotFound` is not reported for `${N_fb}`

#### Scenario: Set environment variable with a variable in its default
- **WHEN** `${Y_%{NE_SET=${S}}}    y` is declared and `NE_SET` is set to `setval`
- **THEN** the variable `${Y_setval}` is defined and no hint is reported for the name

#### Scenario: Unset environment variable without default
- **WHEN** `${U_%{NE_UNSET}}    v` is declared and `NE_UNSET` is not set
- **THEN** the error `VariableNameNotResolvable` is reported, as before

### Requirement: Environment variable in a referenced variable name

On Robot Framework 7.0 and newer, when a `${...}`, `@{...}` or `&{...}` reference has a name with nested variables that contains an environment variable which is not statically resolvable by the rule of the requirement "Environment variables that are not statically resolvable", RobotCode SHALL report the hint `VariableReferenceNotStaticallyResolvable` on the reference and SHALL NOT record a reference to any variable for it.

#### Scenario: Default of an unset environment variable contains a variable
- **WHEN** a test contains `Log    ${NAME_%{NE_X=${S}}}` with `${S}` = `suffix`, `NE_X` not set and `${NAME_suffix}` declared
- **THEN** the hint `VariableReferenceNotStaticallyResolvable` is reported on the reference and no reference to `${NAME_suffix}` is recorded

#### Scenario: Name of the environment variable contains a variable
- **WHEN** a test contains `Log    ${NAME_%{NE_A_${S}}}` with `NE_A_suffix` set
- **THEN** the hint `VariableReferenceNotStaticallyResolvable` is reported on the reference

### Requirement: Resolving references with environment variables in their names

A reference whose environment variable is statically resolvable SHALL be resolved and recorded as before. The hint `VariableReferenceNotStaticallyResolvable` and the recorded references SHALL be identical whether the semantic-model analysis path is enabled or not.

#### Scenario: Name of the environment variable contains a variable, default without variables
- **WHEN** a test contains `Log    ${USED_%{NE_${S}=fb}}` with `NE_suffix` not set and `${USED_fb}` declared
- **THEN** a reference to `${USED_fb}` is recorded and no hint is reported

#### Scenario: Statically resolvable environment variable
- **WHEN** a test contains `Log    ${NAME_%{NE_SET=${S}}}` with `NE_SET` set to `setval` and `${NAME_setval}` declared
- **THEN** a reference to `${NAME_setval}` is recorded and no hint is reported

### Requirement: Environment variable references with a not statically resolvable environment variable

For a reference whose outer variable is `%{...}` and whose text contains an environment variable that is not statically resolvable, the semantic-model analysis path SHALL report the hint `VariableReferenceNotStaticallyResolvable` and the legacy path SHALL NOT, as for a `%{...}` reference with another nested value that cannot be resolved statically.

#### Scenario: Environment variable reference with such an environment variable in its name
- **WHEN** a test contains `Log    %{%{NE_N_${S}}=x}` with `${S}` = `suffix`
- **THEN** the hint `VariableReferenceNotStaticallyResolvable` is reported on the reference when the semantic-model analysis path is enabled, and not when it is disabled
