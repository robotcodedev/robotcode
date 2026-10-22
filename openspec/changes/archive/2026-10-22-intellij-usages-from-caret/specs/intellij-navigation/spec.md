# Spec Delta

## ADDED Requirements

### Requirement: Usages of an import

In a Robot Framework file, Find Usages and Show Usages on the name of a library or resource import SHALL list the imports of that library or file and the calls with its name as prefix.

#### Scenario: Find Usages on a resource import

- **WHEN** Find Usages starts on `../resources/shop.resource` in `Resource    ../resources/shop.resource`
- **THEN** the Find tool window lists the imports of `shop.resource` and the call `shop.Open Shop As`

#### Scenario: Show Usages on a resource import

- **WHEN** Show Usages starts on `../resources/shop.resource` in `Resource    ../resources/shop.resource`
- **THEN** a popup lists the imports of `shop.resource` and the call `shop.Open Shop As`

#### Scenario: Library import

- **WHEN** Find Usages starts on `Collections` in `Library    Collections`
- **THEN** the Find tool window lists the imports of `Collections` and the calls with the prefix `Collections.`, as before

### Requirement: Usages search from the name at the caret

In a Robot Framework file, Find Usages and Show Usages started in the editor SHALL search from the name at the caret, also when that name resolves to a place in a Robot Framework file. Started from another view, such as the Structure tool window, they SHALL behave as before and SHALL NOT search from the caret of an editor.

#### Scenario: Prefix of a resource call

- **WHEN** Find Usages starts on `shop` in `shop.Open Shop As    alice`
- **THEN** the Find tool window lists the imports of `shop.resource` and the calls with the prefix `shop.`

#### Scenario: Use of a keyword argument

- **WHEN** Show Usages starts on `${user}` in `Log In    ${user}    ${password}` in the body of `Open Shop As`
- **THEN** the popup lists the declaration and the uses of `${user}`, under the title "Argument user"

#### Scenario: Keyword from a resource file

- **WHEN** Find Usages starts on `Open Shop As` in `Given Open Shop As    bob`
- **THEN** the Find tool window lists the definition and the calls of `Open Shop As`, as before

#### Scenario: Structure tool window

- **WHEN** the caret of the editor rests on `Log` and Find Usages starts on the keyword `Open Shop As` in the Structure tool window of `shop.resource`
- **THEN** the result is the same as before this change, and no search for `Log` starts
