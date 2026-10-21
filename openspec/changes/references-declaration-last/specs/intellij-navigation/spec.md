# Spec Delta

## ADDED Requirements

### Requirement: LSP Reference(s) shows the usages of library keywords and file variables

In a Robot Framework file, **LSP Reference(s)** SHALL show the usages of a keyword from a library and of a variable from a Python variables file, together with the definition, as it does for a keyword from a resource file.

#### Scenario: Library keyword

- **WHEN** LSP Reference(s) runs on `Log` in `Log    Opened ${BASE_URL} as ${user}`
- **THEN** a popup lists the calls of `Log` in the project and the definition of `Log`

#### Scenario: Library keyword after a prefix

- **WHEN** LSP Reference(s) runs on `Append To List` in `Collections.Append To List    ${items}    b`
- **THEN** a popup lists the calls of `Append To List` and its definition

#### Scenario: Variable from a Python variables file

- **WHEN** LSP Reference(s) runs on `${GREETING}`, which a suite imports from a Python variables file
- **THEN** a popup lists the uses of `${GREETING}` and its definition in the Python file

#### Scenario: Keyword from a resource file

- **WHEN** LSP Reference(s) runs on `Add To Cart`, a keyword of a resource file
- **THEN** a popup lists the calls of `Add To Cart` and its definition, as before
