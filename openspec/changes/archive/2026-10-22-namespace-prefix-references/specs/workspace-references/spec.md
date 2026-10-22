# Spec Delta

## ADDED Requirements

### Requirement: References on the prefix of a keyword call

Find References on the prefix of a keyword call SHALL return the same locations as on the import that the prefix names: for a library or resource file every import of it and every call with its name as prefix, for an alias every call with that alias as prefix. A library that Robot Framework imports by itself SHALL count as imported.

#### Scenario: Library prefix

- **WHEN** Find References runs on `Collections` in `Collections.Append To List    ${items}    b`, in a suite that imports `Collections`
- **THEN** the result lists the imports of `Collections` and the calls with the prefix `Collections.` in the workspace
- **AND** it is the same as on `Collections` in `Library    Collections`

#### Scenario: Resource prefix

- **WHEN** Find References runs on `shop` in `shop.Open Shop As    alice`, in a suite that imports `shop.resource`
- **THEN** the result lists the imports of `shop.resource` and the calls with the prefix `shop.` in the workspace
- **AND** it is the same as on the import of `shop.resource`

#### Scenario: Alias prefix

- **WHEN** Find References runs on `lib_hello` in `lib_hello.A Library Keyword`, in a suite that imports a library `WITH NAME    lib_hello`
- **THEN** the result lists the calls with the prefix `lib_hello.`
- **AND** it is the same as on the alias `lib_hello` in the import

#### Scenario: Library without an import

- **WHEN** Find References runs on `BuiltIn` in `BuiltIn.Log To Console    hi`
- **THEN** the result lists the calls with the prefix `BuiltIn.` in the workspace

#### Scenario: Keyword after a prefix

- **WHEN** Find References runs on `Log To Console` in `BuiltIn.Log To Console    hi`
- **THEN** the result lists the calls of the keyword `Log To Console`, as before
