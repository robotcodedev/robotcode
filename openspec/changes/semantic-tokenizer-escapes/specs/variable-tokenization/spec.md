# Spec Delta

## Purpose

Defines how RobotCode splits a variable that contains backslash escapes into its parts and nested variables on the semantic-model analysis path and in the REPL prompt, so that the variable ends and nested variables are found where Robot Framework finds them.

## ADDED Requirements

### Requirement: Escaped braces and brackets do not end a variable

When the semantic-model analysis path or the REPL prompt splits a variable into its parts and nested variables, a `{`, `}`, `[` or `]` inside it that follows an odd number of backslashes SHALL neither open nor close the variable or one of its items, as in Robot Framework; after an even number of backslashes it SHALL. A variable SHALL extend to the brace or bracket that closes it in Robot Framework: variables nested after an escaped brace SHALL be analyzed like any other nested variable, reported with `VariableNotFound` when they are not defined (an environment variable without default with `EnvironmentVariableNotFound` when it is not set) and recorded as references when they are, and the REPL prompt SHALL show every character of the variable. The name under which the variable itself is looked up is not part of this requirement.

#### Scenario: Undefined variable after an escaped closing brace in a default
- **WHEN** `Log    %{NAME=\}${UNDEF}}` is analyzed on the semantic-model path, with `NAME` not set and `${UNDEF}` not defined
- **THEN** the error `VariableNotFound` "Variable '${UNDEF}' not found." is reported on `UNDEF`, as Robot Framework fails with this message
- **AND** no diagnostic is reported for the environment variable

#### Scenario: Undefined variable after an escaped opening brace in a default
- **WHEN** `Log    %{NAME=\{${UNDEF}}` is analyzed on the semantic-model path
- **THEN** the error "Variable '${UNDEF}' not found." is reported on `UNDEF`

#### Scenario: Undefined variable in the name of an environment variable with a default
- **WHEN** `Log    %{NAME_\}${UNDEF}=d}` is analyzed on the semantic-model path
- **THEN** the error "Variable '${UNDEF}' not found." is reported on `UNDEF`
- **AND** no diagnostic is reported for the environment variable

#### Scenario: Undefined variable in a variable name
- **WHEN** `Log    ${A\}${UNDEF}}` or `Log    @{A\{${UNDEF}}` is analyzed on the semantic-model path and `${A}` is not defined
- **THEN** the error "Variable '${UNDEF}' not found." is reported on `UNDEF`, and nothing is reported for the outer variable

#### Scenario: Unset environment variable after an escaped brace
- **WHEN** `Log    ${A\}%{NAME_UNSET}}` is analyzed on the semantic-model path with `NAME_UNSET` not set
- **THEN** the error `EnvironmentVariableNotFound` "Environment variable '%{NAME_UNSET}' not found." is reported on `NAME_UNSET`, as Robot Framework fails with this message

#### Scenario: Value in the Variables section
- **WHEN** `${V}    %{NAME=\}${UNDEF}}` in `*** Variables ***` is analyzed on the semantic-model path
- **THEN** the error "Variable '${UNDEF}' not found." is reported on `UNDEF`

#### Scenario: Defined variable after an escaped brace
- **WHEN** `${USED}` is defined in `*** Variables ***` and used only in `Log    %{NAME=\}${USED}}`, analyzed on the semantic-model path with unused variables collected
- **THEN** the use is a reference of `${USED}` that references and hover find, and `${USED}` is not reported as not used

#### Scenario: Escaped brace in a default without a nested variable
- **WHEN** `Log    %{NAME=a\}b}` is analyzed on the semantic-model path with `NAME` not set
- **THEN** no diagnostic is reported, as Robot Framework logs `a}b`

#### Scenario: Escaped brace in the REPL prompt
- **WHEN** `Log    %{NAME=a\}b}` is typed in the REPL prompt
- **THEN** the prompt shows `Log    %{NAME=a\}b}` with the environment variable coloured in its parts and no character replaced by a space

#### Scenario: Escaped bracket in an item in the REPL prompt
- **WHEN** `Log    ${D}[a\]b]` is typed in the REPL prompt
- **THEN** the prompt shows `Log    ${D}[a\]b]`, with `[a\]b]` coloured as one item

### Requirement: An escaped variable inside a variable is not a nested variable

When the semantic-model analysis path or the REPL prompt splits a variable into its parts and nested variables, a variable identifier that follows an odd number of backslashes SHALL NOT start a nested variable, as Robot Framework does not resolve it; after an even number of backslashes it SHALL. This applies to `$`, `@`, `&` and `%` inside a variable name or an inline Python expression `${{…}}`, and to `$`, `@` and `&` inside an item.

#### Scenario: Escaped variable in a variable name
- **WHEN** `Log    ${A_\${UNDEF}}` is analyzed on the semantic-model path
- **THEN** no diagnostic is reported for `${UNDEF}`

#### Scenario: Escaped variable in an inline Python expression
- **WHEN** `Log    ${{ '\${UNDEF}' }}` or `Log    ${{ '\%{NAME_UNSET}' }}` is analyzed on the semantic-model path, with `NAME_UNSET` not set
- **THEN** no diagnostic is reported, as the test passes in Robot Framework

#### Scenario: Escaped backslash before a nested variable
- **WHEN** `Log    ${A_\\${UNDEF}}` is analyzed on the semantic-model path
- **THEN** the error "Variable '${UNDEF}' not found." is reported on `UNDEF`, as Robot Framework fails with this message

#### Scenario: Escaped variable in the REPL prompt
- **WHEN** `Log    ${A_\${x}}` is typed in the REPL prompt
- **THEN** `\${x}` is not coloured as a nested variable

### Requirement: Nested variables are analyzed the same on both analysis paths

For variables nested inside a variable that contains backslash escapes, RobotCode SHALL report the same diagnostics and record the same references whether the semantic-model analysis path is enabled or not.

#### Scenario: Both paths
- **WHEN** each of the lines of the scenarios above is analyzed once with the semantic-model analysis path enabled and once with it disabled
- **THEN** the diagnostics and references for the nested variables are identical
