# Spec Delta

## ADDED Requirements

### Requirement: LSP Reference(s) on a prefix shows the usages of its library or resource

In a Robot Framework file, **LSP Reference(s)** on the prefix of a keyword call SHALL show the imports and the prefixed calls of the library or resource file that the prefix names.

#### Scenario: Library prefix

- **WHEN** LSP Reference(s) runs on `Collections` in `Collections.Append To List    ${items}    b`
- **THEN** a popup lists the imports of `Collections` and the calls with the prefix `Collections.`

#### Scenario: Resource prefix

- **WHEN** LSP Reference(s) runs on `shop` in `shop.Open Shop As    alice`
- **THEN** a popup lists the imports of `shop.resource` and the calls with the prefix `shop.`

#### Scenario: Library without an import

- **WHEN** LSP Reference(s) runs on `BuiltIn` in `BuiltIn.Log    ${arg2}`, in a project with a second call prefixed with `BuiltIn.`
- **THEN** a popup lists both calls
