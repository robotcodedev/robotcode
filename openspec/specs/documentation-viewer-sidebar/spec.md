# Spec: documentation-viewer-sidebar

## Purpose

Defines the sidebar of RobotCode's documentation viewer for the page of a library, resource file or suite file, as `robotcode doc browse` and the REPL's `.doc` show it: what it lists, when it is available and shown, how its filter selects entries, how an entry jumps to its heading, and how it is laid out in wide and narrow terminals.

## Requirements

### Requirement: Sidebar with the outline of a library page

When the documentation viewer shows the page of a library, resource file or suite file, from `robotcode doc browse` or from `.doc` in the REPL or at a `robot-debug` stop, pressing `s` SHALL show a sidebar with the outline of the page: every level-2 heading of the page and, below each of them, its level-3 headings, in the order of the page. For the page of a library these are the introduction with its sections, `Importing`, `Keywords` with every keyword, and `Data types` with every data type, as far as the page has them. The sidebar SHALL be hidden when the viewer opens. Other documents of the viewer, such as `.help`, `.kw` and `.source`, SHALL have no sidebar, and `s` SHALL have no effect there.

#### Scenario: Keywords of a library
- **WHEN** `robotcode doc browse Collections` runs in an interactive terminal and `s` is pressed
- **THEN** the sidebar lists `Introduction`, `Keywords` and, below `Keywords`, `Append To List`, `Combine Lists` and every other keyword of the page, in the order of the page

#### Scenario: Hidden at the start
- **WHEN** the viewer opens the page of `Collections`
- **THEN** no sidebar is shown and the page uses the full width of the viewer

#### Scenario: Keyword view of the REPL
- **WHEN** `.kw Log` shows the documentation of `Log` in the viewer and `s` is pressed
- **THEN** no sidebar is shown

### Requirement: Filter while typing

The sidebar SHALL have a filter field that has the focus while the sidebar is being used. Typing SHALL narrow the entries to those whose text contains the filter text, with `*` and `?` as wildcards and case, spaces and underscores ignored, as the patterns of `robotcode doc keywords` select keywords. A level-2 entry SHALL stay listed while it or one of its level-3 entries matches. An empty filter SHALL list every entry. The up and down keys SHALL move the selection through the listed entries, and the list SHALL scroll to show the selected entry. The mouse wheel over the list SHALL scroll the list without changing the selection.

#### Scenario: Part of a name
- **WHEN** the sidebar of the `Collections` page is open and `dict` is typed
- **THEN** every listed level-3 entry contains `dict`, `Keywords` stays listed above the matching keywords, and `Append To List` is not listed

#### Scenario: Wildcard and underscores
- **WHEN** `get*list` or `get_from_list` is typed into the filter of the `Collections` page
- **THEN** `Get From List` is listed

#### Scenario: Empty filter
- **WHEN** the filter text is deleted
- **THEN** every entry of the outline is listed again

### Requirement: Jump to a heading

`Enter` on the selected entry, or a click on an entry, SHALL scroll the page to the heading of that entry. The position before the jump SHALL be added to the viewer's back history, so that `[` returns to it. `Esc` in the sidebar SHALL hide the sidebar and return the focus to the page without jumping.

#### Scenario: Jump and back
- **WHEN** `Get Match Count` is selected in the sidebar of the `Collections` page and `Enter` is pressed
- **THEN** the page shows the heading `Get Match Count`
- **AND** `[` returns to the position before the jump

#### Scenario: Hide without jumping
- **WHEN** `Esc` is pressed in the sidebar
- **THEN** the sidebar is hidden and the page shows the same position as before

### Requirement: Layout in wide and narrow terminals

When the terminal is wide enough for the sidebar and at least 60 columns of page next to it, the sidebar SHALL stand left of the page, and the page SHALL be rendered in the remaining width. After a jump the sidebar SHALL stay visible and the focus SHALL move to the page; `s` SHALL move the focus back to the sidebar. While the sidebar stands beside the page, `Esc` on the page SHALL hide the sidebar instead of closing the viewer; only a further `Esc` SHALL close the viewer. When the sidebar is shown or hidden this way, the heading at the top of the page SHALL stay at the top. In a narrower terminal, the sidebar SHALL lie over the left part of the page, the page SHALL keep its width, and the sidebar SHALL close after a jump.

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
