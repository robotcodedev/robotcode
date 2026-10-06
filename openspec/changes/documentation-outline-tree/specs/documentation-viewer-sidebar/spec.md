# Spec Delta

## MODIFIED Requirements

### Requirement: Sidebar with the outline of a library page

When the documentation viewer shows the page of a library, resource file or suite file, from `robotcode doc browse` or from `.doc` in the REPL or at a `robot-debug` stop, pressing `s` SHALL show a sidebar with the outline of the page: every level-2 heading of the page, below each of them its level-3 headings, and below each section of the introduction its subsections, to any depth, in the order of the page and indented by their depth. For the page of a library these are the introduction with its sections and their subsections, `Importing`, `Keywords` with every keyword, and `Data types` with every data type, as far as the page has them. Keywords, data types and the entries of `Importing` SHALL have no entries below them. The sidebar SHALL be hidden when the viewer opens. Other documents of the viewer, such as `.help`, `.kw` and `.source`, SHALL have no sidebar, and `s` SHALL have no effect there.

#### Scenario: Keywords of a library
- **WHEN** `robotcode doc browse Collections` runs in an interactive terminal and `s` is pressed
- **THEN** the sidebar lists `Introduction`, `Keywords` and, below `Keywords`, `Append To List`, `Combine Lists` and every other keyword of the page, in the order of the page

#### Scenario: Subsections of the introduction
- **WHEN** the sidebar is opened for a library whose introduction has the section `= Section A =` with the subsection `== Sub A1 ==`
- **THEN** the sidebar lists `Sub A1` below `Section A`, indented one step further

#### Scenario: Hidden at the start
- **WHEN** the viewer opens the page of `Collections`
- **THEN** no sidebar is shown and the page uses the full width of the viewer

#### Scenario: Keyword view of the REPL
- **WHEN** `.kw Log` shows the documentation of `Log` in the viewer and `s` is pressed
- **THEN** no sidebar is shown

### Requirement: Filter while typing

The sidebar SHALL have a filter field that has the focus while the sidebar is being used. Typing SHALL narrow the entries to those whose text contains the filter text, with `*` and `?` as wildcards and case, spaces and underscores ignored, as the patterns of `robotcode doc keywords` select keywords. An entry SHALL stay listed while it or one of the entries below it matches. An empty filter SHALL list every entry. The up and down keys SHALL move the selection through the listed entries, and the list SHALL scroll to show the selected entry. The mouse wheel over the list SHALL scroll the list without changing the selection.

#### Scenario: Part of a name
- **WHEN** the sidebar of the `Collections` page is open and `dict` is typed
- **THEN** every listed level-3 entry contains `dict`, `Keywords` stays listed above the matching keywords, and `Append To List` is not listed

#### Scenario: Subsection
- **WHEN** `sub a1` is typed into the filter of the page of a library whose introduction has the section `Section A` with the subsection `Sub A1`
- **THEN** `Introduction`, `Section A` and `Sub A1` are listed

#### Scenario: Wildcard and underscores
- **WHEN** `get*list` or `get_from_list` is typed into the filter of the `Collections` page
- **THEN** `Get From List` is listed

#### Scenario: Empty filter
- **WHEN** the filter text is deleted
- **THEN** every entry of the outline is listed again
