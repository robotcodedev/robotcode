# Spec Delta

## ADDED Requirements

### Requirement: The declaration comes after the usages

When Find References includes the declaration, the language server SHALL list it after all other locations, for keywords and for variables. Without the declaration, the result SHALL list only the usages. The set of locations SHALL be the same in any order.

#### Scenario: Library keyword

- **WHEN** Find References with the declaration runs on a call of `Log`
- **THEN** the last location is the definition of `Log` in the BuiltIn library's Python file
- **AND** every location before it is a call of `Log`

#### Scenario: Variable from a Python variables file

- **WHEN** Find References with the declaration runs on `${A_VAR_FROM_LIB}`, which a suite imports from a Python variables file
- **THEN** the last location is the variable's definition in that Python file

#### Scenario: Keyword from a resource file

- **WHEN** Find References with the declaration runs on a call of a keyword that a resource file defines
- **THEN** the last location is the keyword's definition in the resource file

#### Scenario: Without the declaration

- **WHEN** Find References without the declaration runs on a call of `Log`
- **THEN** the result lists the calls of `Log` and not its definition
