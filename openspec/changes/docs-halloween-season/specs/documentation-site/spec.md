# Spec Delta

## MODIFIED Requirements

### Requirement: Home page

The home page SHALL show the product name and tagline, one picture of the RobotCode artwork chosen at random on each load, a subline chosen at random, actions to get started and to install the VS Code and JetBrains extensions, links to the GitHub repository and to sponsoring, the feature overview, the RoboCon 2024 tutorial video, the sponsoring options and the supporters. While a season of the site is active that has a picture of its own, the home page SHALL show that picture first instead of a random one; outside that season the picture SHALL NOT be part of the gallery. Previous and next buttons and a horizontal swipe on the picture SHALL switch to the neighbouring picture. Clicking the picture SHALL open an enlarged view that closes on a click or Escape and in which the left and right arrow keys switch pictures. Every feature card that links to a page SHALL link to the page that covers the feature.

#### Scenario: Random picture
- **WHEN** the home page is loaded
- **THEN** one picture of the RobotCode artwork is shown next to the product name
- **AND** the actions Get Started, Install VS Code and Install JetBrains are offered

#### Scenario: Season picture
- **WHEN** the home page is loaded during the Halloween season and the site has a Halloween picture
- **THEN** the Halloween picture is shown next to the product name
- **AND** the next button switches to the other pictures of the RobotCode artwork

#### Scenario: Browsing the pictures
- **WHEN** a reader swipes left on the picture, or clicks it and presses the right arrow key
- **THEN** the next picture is shown, in the enlarged view in the second case
- **AND** Escape closes the enlarged view

#### Scenario: Feature card target
- **WHEN** a reader follows the link of the "REPL & notebooks" feature card
- **THEN** the REPL guide `/guides/repl/` is shown
