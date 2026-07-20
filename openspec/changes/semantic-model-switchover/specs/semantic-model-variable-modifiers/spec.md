# Spec: semantic-model-variable-modifiers

## ADDED Requirements

### Requirement: Semantic tokens carry variable type modifiers

The model semantic-tokens renderer SHALL emit variable type modifiers (local, global, builtin, environment) on variable tokens, derived from the resolved `VariableDefinition.type` obtained via `model.find_variable(value, line)`. This is a new capability the legacy `KeywordTokenAnalyzer` path did not provide; it is additive and requires no additional resolution pass.

#### Scenario: Builtin variable modifier

- **WHEN** semantic tokens are rendered for a reference to `${CURDIR}`
- **THEN** the variable token carries the builtin modifier bit

#### Scenario: Local variable modifier

- **WHEN** semantic tokens are rendered for a reference to a FOR loop variable inside the loop body
- **THEN** the variable token carries the local modifier bit

#### Scenario: Modifiers are the only sanctioned deviation from legacy output

- **WHEN** the Level-D parity fixture compares model output to legacy output
- **THEN** the variable type modifier bits are the only permitted difference; all other token data remains identical
