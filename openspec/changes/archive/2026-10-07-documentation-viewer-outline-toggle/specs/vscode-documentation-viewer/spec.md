# Spec Delta

## MODIFIED Requirements

### Requirement: Outline of a viewer

Next to the page, the viewer SHALL show an outline as a tree while the outline is shown (requirement "Showing and hiding the outline"), like the sidebar of the REPL's documentation viewer: the level-2 headings of the page, below each of them its level-3 headings, and below each section of the introduction its subsections, to any depth. Keywords, data types and the entries of `Importing` SHALL have no entries below them.

#### Scenario: Subsections of the introduction
- **WHEN** a viewer shows a library whose introduction has the section `= Section A =` with the subsection `== Sub A1 ==`
- **THEN** the outline lists `Sub A1` below `Section A`, and `Section A` below `Introduction`
- **AND** with the focus on `Sub A1`, Left moves the focus to `Section A`, and Left on the expanded `Section A` collapses it

### Requirement: A viewer keeps its state

A viewer SHALL keep its target, position, history, filter, whether its outline is shown, and the state of its pin button when its tab is hidden and shown again, when it is moved, and after a reload of the window. Splitting or copying a viewer and reopening a closed viewer are not required.

#### Scenario: Moved into another editor group
- **WHEN** a viewer shows `XML` with the filter `list` and is moved into another editor group
- **THEN** it shows `XML` at the same position with the filter `list`

#### Scenario: Hidden outline after a reload
- **WHEN** the window is reloaded while a viewer that shows `XML` has its outline hidden
- **THEN** the viewer shows `XML` with its outline hidden

## ADDED Requirements

### Requirement: Showing and hiding the outline

The toolbar of a viewer SHALL have a button that hides and shows the outline together with its filter field. While the outline is hidden, the page SHALL take the full width of the viewer. Hiding or showing the outline SHALL NOT move the page, and SHALL keep the filter text, the collapsed entries and the width of the outline. When the outline is shown again, its selected entry SHALL be visible.

#### Scenario: Hide the outline
- **WHEN** a viewer shows `BuiltIn` at `Should Be Equal` and the user clicks the outline button
- **THEN** the outline and its filter field are hidden, the page takes the full width of the viewer, and it still shows `Should Be Equal`

#### Scenario: Show the outline again
- **WHEN** the outline of a viewer that shows `BuiltIn` is hidden, the user clicks the link `Should Be Equal` in the introduction, and then clicks the outline button
- **THEN** the outline is shown with its earlier width, and `Should Be Equal` is selected and visible in it

### Requirement: Outline of new viewers

The setting `robotcode.documentationViewer.showOutline` SHALL decide whether a new viewer starts with its outline shown, and SHALL be `true` by default. A viewer restored from a state that does not record whether its outline is shown SHALL start as the setting says. A change of the setting SHALL NOT show or hide the outline of an open viewer.

#### Scenario: New viewer
- **WHEN** the user opens a new viewer while another viewer has its outline hidden
- **THEN** the new viewer shows its outline

#### Scenario: New viewer without the outline
- **WHEN** `robotcode.documentationViewer.showOutline` is `false` and the user runs "RobotCode: Open Documentation Viewer"
- **THEN** the new viewer shows `BuiltIn` with its outline hidden, and the outline button shows the outline when clicked

#### Scenario: Setting changed while a viewer is open
- **WHEN** a viewer shows its outline and the user sets `robotcode.documentationViewer.showOutline` to `false`
- **THEN** that viewer keeps its outline, and the next new viewer starts without it
