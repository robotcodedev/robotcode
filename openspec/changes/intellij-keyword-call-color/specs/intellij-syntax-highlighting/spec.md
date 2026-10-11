# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Keyword calls and names inherit from Function declaration`
- TO: `### Requirement: Keyword calls inherit from Function call, names from Function declaration`

## MODIFIED Requirements

### Requirement: Token classes inherit from matching general language colours

Each Robot Framework colour setting SHALL inherit from the general language colour that matches the category the VS Code extension gives the token, so that the plugin makes no assumption about any particular colour scheme:
- variables inherit from *Instance field*;
- arguments inherit from *String*;
- section headers, settings, control flow, `VAR` and BDD prefixes inherit from *Keyword*.

Whether and how a general language colour is coloured is up to the colour scheme.

#### Scenario: Inheritance on the colour settings page
- **WHEN** the user selects "Keyword call" and then "Variable" on the Robot Framework colour settings page of an unmodified scheme
- **THEN** "Keyword call" inherits from the language default *Function call*, and "Variable" from *Instance field*

#### Scenario: Scheme that colours both categories
- **WHEN** the active scheme gives *Function call* and *Instance field* different colours, and a test case containing `Log    ${message}` is shown
- **THEN** `Log` has the function call colour and `${message}` has the instance field colour

#### Scenario: Scheme that leaves a category uncoloured
- **WHEN** the active scheme gives *Function call* no colour of its own
- **THEN** keyword calls are shown as plain text, like function calls in the scheme's other languages

#### Scenario: BDD prefix
- **WHEN** a step `Given the user is logged in` is shown
- **THEN** `Given` has the keyword colour and the rest of the step has the keyword call colour

### Requirement: Keyword calls inherit from Function call, names from Function declaration

Keyword calls SHALL inherit from *Function call*, so that they look like function calls in the colour scheme's other languages. Test case names and keyword names SHALL inherit from *Function declaration*.

#### Scenario: Name settings on the colour settings page
- **WHEN** the user selects "Test case name" and then "Keyword name" on the Robot Framework colour settings page of an unmodified scheme
- **THEN** both inherit from the language default *Function declaration*

#### Scenario: Scheme that colours declarations but not calls
- **WHEN** the active scheme colours *Function declaration* but gives *Function call* no colour of its own, and a test case `Greet` that calls `Log    hello` is shown
- **THEN** `Greet` has the function declaration colour and `Log` is shown as plain text

### Requirement: Correcting tokens apply their colour setting

Where a token corrects what the grammar-based highlighting shows, its colour setting SHALL apply even if it resolves to the plain-text look, because the grammar-based look belongs to another category there. This applies to type hints, named arguments, namespaces, operators, keyword calls, BDD prefixes, arguments, control-flow words and options, and errors. A token type the plugin does not list as correcting SHALL be treated as refining.

#### Scenario: Keyword call with a plain-text colour
- **WHEN** the active scheme gives *Function call* no colour of its own, and `Log    message` is shown
- **THEN** `Log` has the plain-text look after semantic highlighting is applied
