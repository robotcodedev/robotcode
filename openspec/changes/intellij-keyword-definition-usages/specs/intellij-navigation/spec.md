## ADDED Requirements

### Requirement: Ctrl+click on a keyword definition shows its usages

In a Robot Framework file, Ctrl+click and **Navigate | Declaration or Usages** on the name of a keyword definition SHALL open the usages popup of that keyword, with the title and the places that Show Usages on that name lists.

#### Scenario: Keyword used in other files

- **WHEN** Ctrl+click on `Open Shop As` in its definition in `shop.resource`
- **THEN** a popup titled "Keyword Open Shop As" lists the definition and the calls in `cart.robot`, `login.robot` and `orders.robot`

#### Scenario: Declaration or Usages

- **WHEN** **Navigate | Declaration or Usages** runs with the caret in `Open Shop As` in its definition in `shop.resource`
- **THEN** the same popup opens

### Requirement: Ctrl+hover on a keyword definition shows its documentation

In a Robot Framework file, holding Ctrl over the name of a keyword definition SHALL underline that name and show the keyword's documentation in the hint, as holding Ctrl over a call of the keyword does.

#### Scenario: Name of a keyword definition

- **WHEN** Ctrl is held and the mouse rests on `Open Shop As` in its definition in `shop.resource`
- **THEN** `Open Shop As` is underlined
- **AND** the hint shows the keyword's documentation with its arguments, as over `Open Shop As` in `Test Setup    Open Shop As    alice`
