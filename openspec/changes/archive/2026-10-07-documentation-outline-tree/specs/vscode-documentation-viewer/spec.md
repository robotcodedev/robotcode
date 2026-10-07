# Spec Delta

## MODIFIED Requirements

### Requirement: The page and its outline

A viewer SHALL show the page that `robotcode doc lib` produces for its target. The page SHALL be rendered by VS Code's built-in Markdown support, styled like VS Code's Markdown preview, and SHALL follow the colour theme.

The viewer SHALL work on desktop, in remote windows, and in VS Code for the Web with a remote extension host, for example a Codespace.

#### Scenario: Filter
- **WHEN** the user types `should be` into the filter field of a viewer that shows `BuiltIn`
- **THEN** the outline lists the section `Keywords` with only the keywords whose names contain `should be`, ignoring case, such as `Should Be Equal` and `Length Should Be`

#### Scenario: Outline keys
- **WHEN** the outline has the focus and the user presses End
- **THEN** its last entry gets the focus and is visible
- **AND** Home moves the focus to its first entry

#### Scenario: Typing in the outline
- **WHEN** the outline of `BuiltIn` has the focus and the user types `sho`
- **THEN** the focus moves to the next entry whose title starts with `Sho`, such as `Should Be Empty`

#### Scenario: Links in the introduction
- **WHEN** the user clicks the entry `String representations` of the table of contents, or the link `Should Be Equal`, in the introduction of `BuiltIn` on Robot Framework 7.5
- **THEN** the page scrolls to that section or keyword

#### Scenario: Link to a data type
- **WHEN** the user clicks the link `Element` in the documentation of `Parse Xml` of `XML` on Robot Framework 7.5
- **THEN** the page scrolls to the heading of the data type `Element`

#### Scenario: Keyword with a non-ASCII name
- **WHEN** "Show in Documentation Viewer" is chosen on a call of the keyword `Öffne Seite` of a resource file
- **THEN** the viewer shows the resource file at the heading `Öffne Seite`

#### Scenario: Script in documentation
- **WHEN** a library documented in HTML format contains a `<script>` element
- **THEN** the element is not executed

#### Scenario: Image map in documentation
- **WHEN** a library documented in HTML format contains an image map with an `<area href="https://example.com">`, and the user clicks the area
- **THEN** the viewer still shows the page

#### Scenario: Outline follows a link
- **WHEN** the user clicks the link `Should Be Equal` in the introduction of `BuiltIn`
- **THEN** the outline selects `Should Be Equal` and scrolls it into view

#### Scenario: Theme change
- **WHEN** the user switches from a light to a dark colour theme while a viewer is open
- **THEN** the toolbar, the outline and the page follow the new theme

#### Scenario: Markdown support disabled
- **WHEN** the built-in extension "Markdown Language Features" is disabled and a viewer shows `BuiltIn`
- **THEN** the viewer shows a notice and the Markdown of the page as text, and the outline lists the keywords and data types of `BuiltIn`

#### Scenario: Remote window
- **WHEN** a viewer is used in a window connected to WSL, SSH or a dev container
- **THEN** it generates and shows pages as in a local window

## ADDED Requirements

### Requirement: Outline of a viewer

Next to the page, the viewer SHALL show an outline as a tree, like the sidebar of the REPL's documentation viewer: the level-2 headings of the page, below each of them its level-3 headings, and below each section of the introduction its subsections, to any depth. Keywords, data types and the entries of `Importing` SHALL have no entries below them.

#### Scenario: Subsections of the introduction
- **WHEN** a viewer shows a library whose introduction has the section `= Section A =` with the subsection `== Sub A1 ==`
- **THEN** the outline lists `Sub A1` below `Section A`, and `Section A` below `Introduction`
- **AND** with the focus on `Sub A1`, Left moves the focus to `Section A`, and Left on the expanded `Section A` collapses it

### Requirement: Filtering the outline of a viewer

The filter field of a viewer's outline SHALL keep the entries whose titles match the filter text by the pattern rules of `robotcode doc keywords`: contains, `*`, `?` and `[…]`/`[!…]`, ignoring case, spaces and underscores. An invalid pattern SHALL match nothing. An entry SHALL stay while it or one of the entries below it matches.

#### Scenario: Filter for a subsection
- **WHEN** the user types `sub a1` into the filter field of that viewer
- **THEN** the outline lists `Introduction`, `Section A` below it and `Sub A1` below that

### Requirement: Choosing and selecting outline entries

Choosing an entry of a viewer's outline SHALL show the page at its heading. The entry of the heading the page was shown at SHALL be selected, also in high contrast themes. When the page is shown at another heading, by a link, an action, back or forward, the outline SHALL scroll that entry into view.

#### Scenario: Choosing a keyword
- **WHEN** the user chooses the entry `Should Be Equal` in the outline of a viewer that shows `BuiltIn`
- **THEN** the page shows `Should Be Equal`, and its entry is selected

### Requirement: Moving through the outline with keys

In a viewer's outline, Up and Down SHALL move the focus to the previous and next visible entry. Right SHALL expand a collapsed entry or move to the first entry below it. Left SHALL collapse an expanded entry or move to the entry it belongs to. Home and End SHALL move to the first and last visible entry. Page Up and Page Down SHALL move by one visible page of entries.

#### Scenario: Right on a collapsed entry
- **WHEN** the focus is on a collapsed entry of the outline with entries below it, and the user presses Right
- **THEN** the entry is expanded

### Requirement: Enter, typing and modifier keys in the outline

In a viewer's outline, Enter SHALL choose the focused entry. Typing SHALL move the focus to the next visible entry whose title starts with the typed text. The outline SHALL NOT consume key combinations with Alt, Ctrl or Cmd.

#### Scenario: Enter on an entry
- **WHEN** an entry of the outline has the focus and the user presses Enter
- **THEN** the page is shown at the heading of that entry

### Requirement: Links in a viewer's page

In the page of a viewer, a link within the page, to a section, a keyword or a data type, SHALL show its target in the page. `http`, `https` and `mailto` links SHALL open outside the viewer. `vscode:` and `vscode-insider:` links, and on desktop links of the product's own URL scheme, SHALL be handled by VS Code. `command:` links and links of other schemes SHALL do nothing.

#### Scenario: Command link
- **WHEN** the user clicks a `command:` link in the documentation that a viewer shows
- **THEN** nothing happens

### Requirement: Documentation content does not run

Scripts, event handlers and forms contained in documentation that a viewer shows SHALL NOT run, and nothing in it SHALL navigate the viewer away from its page.

#### Scenario: Event handler in documentation
- **WHEN** a library documented in HTML format contains an element with an `onclick` handler, and the user clicks the element
- **THEN** the handler does not run

### Requirement: A viewer without Markdown support

When VS Code's built-in Markdown support is disabled, the viewer SHALL show a notice and the page as plain Markdown text. The outline SHALL then list the keywords and data types; choosing one of them is not required to scroll or to add a history entry.

#### Scenario: Keywords without Markdown support
- **WHEN** the built-in extension "Markdown Language Features" is disabled and a viewer shows `Collections`
- **THEN** the outline lists the keywords of `Collections`
