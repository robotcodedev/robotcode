# Spec Delta

## ADDED Requirements

### Requirement: Ctrl+hover underlines the name under the mouse

In a Robot Framework file, holding Ctrl over the name of a keyword call, a library or resource prefix, an import or a variable SHALL underline that name as the language server marks it, and nothing beyond it. A keyword call SHALL be underlined also in a setting such as `Test Setup` and as an argument of another keyword.

#### Scenario: Keyword call

- **WHEN** Ctrl is held and the mouse rests on `Add To Cart` in `Add To Cart    coffee`
- **THEN** `Add To Cart` is underlined

#### Scenario: Keyword in a setting

- **WHEN** Ctrl is held and the mouse rests on `Open Shop As` in `Test Setup    Open Shop As    alice`
- **THEN** `Open Shop As` is underlined

#### Scenario: Keyword as an argument of another keyword

- **WHEN** Ctrl is held and the mouse rests on `Open Shop As` in `Run Keyword And Expect Error    Wrong password    Open Shop As    alice`
- **THEN** `Open Shop As` is underlined

#### Scenario: Keyword after a prefix

- **WHEN** Ctrl is held and the mouse rests on `Log` in `BuiltIn.Log    ${arg2}`
- **THEN** only `Log` is underlined

#### Scenario: Prefix of a keyword call

- **WHEN** Ctrl is held and the mouse rests on `BuiltIn` in `BuiltIn.Log    ${arg2}`
- **THEN** only `BuiltIn` is underlined

#### Scenario: Keyword whose name contains a dot

- **WHEN** a suite defines a keyword `Shop.Open` and Ctrl is held with the mouse on `Shop.Open` in a call of it
- **THEN** `Shop.Open` is underlined as one name

#### Scenario: Variable with a type

- **WHEN** Ctrl is held and the mouse rests on `arg2` in `[Arguments]    ${arg1}    ${arg2: str}`
- **THEN** `arg2` is underlined, without `: str`

### Requirement: Ctrl+click goes to the target of the name under the mouse

In a Robot Framework file, Ctrl+click on the name of a keyword call, a library or resource prefix or an import SHALL go to the target of that name: the keyword's definition, the library or resource the prefix names, or the import.

#### Scenario: Keyword after a prefix

- **WHEN** Ctrl+click on `Log` in `BuiltIn.Log    ${arg2}`
- **THEN** the definition of the keyword `Log` of the BuiltIn library opens

#### Scenario: Prefix of an imported library

- **WHEN** Ctrl+click on `Collections` in `Collections.Append To List    ${items}    b`, in a file that has `Library    Collections`
- **THEN** the editor goes to that `Library    Collections` import

#### Scenario: Keyword in a setting

- **WHEN** Ctrl+click on `Open Shop As` in `Test Setup    Open Shop As    alice`
- **THEN** the definition of `Open Shop As` in `shop.resource` opens

### Requirement: The Ctrl+hover hint describes the target of the name

Holding Ctrl over a name in a Robot Framework file SHALL show the hint of that name's target, not of another part of the same cell.

#### Scenario: Keyword after a prefix

- **WHEN** Ctrl is held and the mouse rests on `Log` in `BuiltIn.Log    ${arg2}`
- **THEN** the hint describes the keyword `Log`, not the library `BuiltIn`

#### Scenario: Prefix of a keyword call

- **WHEN** Ctrl is held and the mouse rests on `Collections` in `Collections.Append To List    ${items}    b`
- **THEN** the hint describes the library `Collections`
