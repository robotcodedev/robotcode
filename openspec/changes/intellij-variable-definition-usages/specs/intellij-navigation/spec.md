## ADDED Requirements

### Requirement: Ctrl+click on a variable definition shows its usages

With the semantic model, Ctrl+click and **Navigate | Declaration or Usages** on the name of a variable or argument where it is defined SHALL open the usages popup of that variable, with the title and the places that Show Usages on that name lists. On an assignment to a variable that already exists, and without the semantic model, Ctrl+click SHALL go to the variable's definition, as it does today.

#### Scenario: Argument of a keyword

- **WHEN** the semantic model is on and Ctrl+click on `user` in `[Arguments]    ${user}    ${password}=secret` of `Open Shop As` in `shop.resource`
- **THEN** a popup titled "Argument user" lists the same places as Show Usages on that name

#### Scenario: Variable of the Variables section

- **WHEN** the semantic model is on and **Navigate | Declaration or Usages** runs with the caret in `GREETING` in `${GREETING}    hello` in `*** Variables ***`
- **THEN** a popup titled "Variable GREETING" lists the same places as Show Usages on that name

#### Scenario: First assignment of a local variable

- **WHEN** the semantic model is on and Ctrl+click on `x` in `${x}=    Set Variable    1`, the first assignment of `${x}` in its test
- **THEN** a popup titled "Variable x" lists the same places as Show Usages on that name

#### Scenario: Assignment to an existing variable

- **WHEN** the semantic model is on and Ctrl+click on `x` in a later `${x}=    Set Variable    2` in the same test
- **THEN** the editor goes to `x` in the first assignment, and no popup opens

#### Scenario: Without the semantic model

- **WHEN** the semantic model is off and Ctrl+click on `x` in the first `${x}=    Set Variable    1`
- **THEN** the caret goes to that name, as it does today, and no popup opens
