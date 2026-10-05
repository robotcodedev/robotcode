# Spec: semantic-model-variable-modifiers

## ADDED Requirements

### Requirement: Built-in variables carry the builtin modifier

The name token of a variable that resolves to a Robot Framework built-in variable (such as `${CURDIR}`, `${EMPTY}`, `${SPACE}` or `${TRUE}`) SHALL carry the builtin modifier. The modifier SHALL be computed when the file is analyzed, from the resolved variable type, and rendering SHALL map it without resolving anything again. This is a new capability the legacy `KeywordTokenAnalyzer` path did not provide.

Variable tokens SHALL carry no other variable type modifier: no local, global or environment modifier.

#### Scenario: Built-in variable

- **WHEN** semantic tokens are rendered for a reference to `${CURDIR}`
- **THEN** the token for `CURDIR` carries the builtin modifier

#### Scenario: Built-in variable with extended syntax

- **WHEN** semantic tokens are rendered for `Log    ${SPACE * 4}`
- **THEN** the token for `SPACE` carries the builtin modifier

#### Scenario: Other variables

- **WHEN** semantic tokens are rendered for a reference to a `FOR` loop variable inside the loop body, and for `%{HOME}`
- **THEN** neither variable token carries a variable type modifier

#### Scenario: The modifier is the only sanctioned deviation from legacy output

- **WHEN** the Level-D parity fixture compares model output to legacy output
- **THEN** the builtin modifier bit on variable tokens is the only permitted difference; all other token data remains identical
