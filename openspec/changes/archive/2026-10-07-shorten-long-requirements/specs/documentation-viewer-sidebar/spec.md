# Spec Delta

## MODIFIED Requirements

### Requirement: Layout in wide and narrow terminals

When the terminal is wide enough for the sidebar and at least 60 columns of page next to it, the sidebar SHALL stand left of the page, and the page SHALL be rendered in the remaining width. After a jump the sidebar SHALL stay visible and the focus SHALL move to the page; `s` SHALL move the focus back to the sidebar. In a narrower terminal, the sidebar SHALL lie over the left part of the page, the page SHALL keep its width, and the sidebar SHALL close after a jump.

#### Scenario: Wide terminal
- **WHEN** the sidebar of the `Collections` page is opened in a terminal with 120 columns and a keyword is chosen with `Enter`
- **THEN** the sidebar stands left of the page and stays visible after the jump, and the page is rendered narrower than without the sidebar

#### Scenario: Esc on the page beside the sidebar
- **WHEN** a keyword of the `Collections` page was chosen in the sidebar in a terminal with 120 columns and `Esc` is pressed
- **THEN** the sidebar is hidden and the viewer stays open
- **AND** a further `Esc` closes the viewer

#### Scenario: Position when showing and hiding
- **WHEN** the page of `Collections` is scrolled to the heading `Get Match Count` in a terminal with 120 columns and the sidebar is shown and hidden again
- **THEN** the heading `Get Match Count` is at the top of the page each time

#### Scenario: Narrow terminal
- **WHEN** the sidebar of the `Collections` page is opened in a terminal with 80 columns and a keyword is chosen with `Enter`
- **THEN** the sidebar lies over the page, the page keeps its width, and the sidebar is closed after the jump

## ADDED Requirements

### Requirement: Esc and position while the sidebar stands beside the page

While the sidebar stands beside the page, `Esc` on the page SHALL hide the sidebar instead of closing the viewer; only a further `Esc` SHALL close the viewer. When the sidebar is shown or hidden this way, the heading at the top of the page SHALL stay at the top.

#### Scenario: Two Esc on the page
- **WHEN** the sidebar stands beside the page of `Collections` in a terminal with 120 columns, the focus is on the page, and `Esc` is pressed twice
- **THEN** the first `Esc` hides the sidebar and the second closes the viewer
