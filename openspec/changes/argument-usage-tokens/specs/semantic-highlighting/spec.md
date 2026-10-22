# Spec Delta

## ADDED Requirements

### Requirement: Uses of arguments are parameters

In a keyword, every name that the analysis resolves to an argument declared in the keyword's `[Arguments]` SHALL get a `parameter` token instead of a `variable` token. This holds for uses and for assignments that set the argument again, and on every analysis path. Embedded arguments of a keyword's name, and variables of any other kind, SHALL keep their tokens.

#### Scenario: Use of an argument

- **WHEN** a keyword with `[Arguments]    ${user}` contains `Log In    ${user}`
- **THEN** `user` in `Log In    ${user}` gets a parameter token, and `${` and `}` get no token

#### Scenario: Argument with item access and extended syntax

- **WHEN** a keyword with `[Arguments]    ${items}    ${name}` contains `Log    ${items}[0]` and `Log    ${name.upper()}`
- **THEN** `items` and `name` get parameter tokens

#### Scenario: Argument inside a nested variable

- **WHEN** a keyword with `[Arguments]    ${key}` contains `Log    ${CONFIG_${key}}`
- **THEN** `key` gets a parameter token

#### Scenario: Argument set again

- **WHEN** a keyword with `[Arguments]    ${user}` contains `${user}=    Set Variable    x`, then `VAR    ${user}    y`, then `Log    ${user}`
- **THEN** `user` gets a parameter token in all three statements

#### Scenario: Settings and steps above the arguments

- **WHEN** a keyword has `[Timeout]    ${limit}` and `Log    ${limit}` above `[Arguments]    ${limit}`
- **THEN** `limit` gets a parameter token in both, because Robot Framework sets the arguments before it runs any of them

#### Scenario: Tags of the keyword

- **WHEN** a keyword with `[Arguments]    ${user}` has `[Tags]    ${user}`
- **THEN** `user` in `[Tags]` gets a variable token, because Robot Framework resolves the tags with the caller's variables

#### Scenario: Local variable of the same keyword

- **WHEN** a keyword with `[Arguments]    ${user}` contains `${greeting}=    Greeting` and `Log    ${greeting}`
- **THEN** `greeting` gets variable tokens

#### Scenario: Embedded argument

- **WHEN** the keyword `Open ${shop} Now` contains `Log    ${shop}`
- **THEN** `shop` gets a variable token in the keyword's name and in `Log    ${shop}`

#### Scenario: Same tokens on the semantic model

- **WHEN** semantic tokens of such a keyword are collected with the semantic model enabled
- **THEN** they are the same as without it
