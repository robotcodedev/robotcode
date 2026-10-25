# Spec Delta

## ADDED Requirements

### Requirement: Spiders ask for a poke

During the Halloween season the home page and the news pages SHALL now and then show a spider saying "Trick or treat? Poke me!" in a speech bubble next to it, for about four seconds: first about ten seconds after the page opens, then about every 45 seconds, until the visitor has got a treat on the page. The hanging spider, the resting spider and the walking spiders SHALL take turns. With reduced motion no spider SHALL ask.

#### Scenario: First invitation
- **WHEN** a visitor stays on the home page or a news post for about ten seconds without clicking a creature
- **THEN** a spider in the window says "Trick or treat? Poke me!" in a speech bubble next to it
- **AND** the bubble disappears after about four seconds

#### Scenario: Taking turns
- **WHEN** the visitor stays on the home page for a few minutes, with the hanging and the resting spider in the window
- **THEN** the hanging spider, the resting spider and a walking spider ask in turn, about every 45 seconds

#### Scenario: Walking spider asks
- **WHEN** it is a walking spider's turn
- **THEN** the spider stops while its bubble is shown and walks on afterwards

#### Scenario: Spider out of view
- **WHEN** the spider whose turn it is is not in the window, such as the hanging spider after the visitor scrolled down
- **THEN** the next spider in the window asks instead

#### Scenario: Poking the bubble
- **WHEN** the visitor clicks the speech bubble
- **THEN** its spider reacts as when it is clicked, and a treat appears

#### Scenario: After a treat
- **WHEN** the visitor clicks a spider, the ghost or the pumpkin and gets a treat
- **THEN** a speech bubble shown at that moment disappears
- **AND** no spider asks again on that page

#### Scenario: Reduced motion
- **WHEN** a visitor whose system asks for reduced motion stays on the home page
- **THEN** no spider asks

## MODIFIED Requirements

### Requirement: Decorations stay out of the way

Seasonal decorations SHALL NOT take clicks, taps or keyboard focus away from the page, except where a visitor clicks a spider, a spider's speech bubble, the ghost or the pumpkin itself. Text under the fog SHALL stay readable, and every decoration SHALL be visible and readable in the light and in the dark theme. Decorations SHALL pause while the browser tab is hidden.

#### Scenario: Clicking a button under the fog
- **WHEN** a visitor clicks a link or button in the part of the window covered by fog
- **THEN** the link or button reacts as without the fog

#### Scenario: Light theme
- **WHEN** a visitor who picked the light theme opens the home page during the season
- **THEN** the spiders, bats, ghost, pumpkin, moon and fog are visible against the light background
