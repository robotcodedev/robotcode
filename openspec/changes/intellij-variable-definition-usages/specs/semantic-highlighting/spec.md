## ADDED Requirements

### Requirement: Variable definitions are declarations with the semantic model

With the semantic model (`robotcode.experimental.semanticModel`), the language server SHALL give the token of a variable or argument name the modifier `declaration` where the variable is defined: in `*** Variables ***`, in `[Arguments]`, as an embedded argument of a keyword name, at the first assignment of a local variable, and in `VAR`, `FOR` and `EXCEPT ... AS`. No other variable token SHALL get it, nor any variable token without the semantic model.

#### Scenario: Declaration in the Variables section

- **WHEN** `*** Variables ***` with `${GREETING}    hello` is analyzed with the semantic model
- **THEN** `GREETING` gets a `variable` token with the modifier `declaration`

#### Scenario: Argument and its use

- **WHEN** a keyword with `[Arguments]    ${user}` and `Log    ${user}` is analyzed with the semantic model
- **THEN** `user` in `[Arguments]` gets a `parameter` token with `declaration`, and `user` in `Log    ${user}` gets a `parameter` token without it

#### Scenario: First and later assignment

- **WHEN** a test with `${x}=    Set Variable    1` and then `${x}=    Set Variable    2` is analyzed with the semantic model
- **THEN** `x` in the first assignment gets `declaration`, and `x` in the second does not

#### Scenario: VAR, FOR and EXCEPT

- **WHEN** a test with `VAR    ${y}    2`, `FOR    ${item}    IN    a    b` and `EXCEPT    AS    ${err}`, and no other variables of these names, is analyzed with the semantic model
- **THEN** `y`, `item` and `err` get `declaration`

#### Scenario: Embedded argument in a keyword name

- **WHEN** the keyword definition `Open ${url} In Browser` is analyzed with the semantic model
- **THEN** `url` in its name gets `declaration`

#### Scenario: Item assignment

- **WHEN** `${DICT}[key]=    Set Variable    x` is analyzed with the semantic model, in a suite whose `*** Variables ***` define `&{DICT}`
- **THEN** `DICT` in the item assignment gets a `variable` token without `declaration`

#### Scenario: Without the semantic model

- **WHEN** the same files are analyzed with `robotcode.experimental.semanticModel` off
- **THEN** no `variable` or `parameter` token has the modifier `declaration`
