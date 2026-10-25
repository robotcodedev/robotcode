## ADDED Requirements

### Requirement: The command Show Documentation Viewer

The command "RobotCode: Show Documentation Viewer" SHALL show the pinned viewer, or else the viewer used last, and give it the focus. The viewer SHALL keep its target, place and history, and a viewer in another window SHALL come to the front there. Without a viewer, the command SHALL open a new viewer on `BuiltIn` as the command New Documentation Viewer does. The command SHALL be in the command palette.

#### Scenario: The viewer used last

- **WHEN** two viewers are open, none is pinned, the user used the viewer that shows `Collections` at `Remove From List` last, a `.robot` file is the active editor, and the user runs the command
- **THEN** the viewer that shows `Collections` is the active editor and has the focus, still at `Remove From List`

#### Scenario: The pinned viewer

- **WHEN** a pinned viewer shows `XML`, the user used another viewer last, and the user runs the command
- **THEN** the viewer that shows `XML` is the active editor and has the focus

#### Scenario: Without a viewer

- **WHEN** no viewer is open, and the user runs the command
- **THEN** a new viewer shows `BuiltIn`, and its target field has the focus with its text selected

#### Scenario: Viewer in another window

- **WHEN** the viewer used last is in another window, and the user runs the command in the main window
- **THEN** the other window comes to the front, and its viewer has the focus

### Requirement: The buttons of the view Documentation Bookmarks

The title of the view Documentation Bookmarks SHALL have the buttons Show Documentation Viewer, New Documentation Viewer and Reset Documentation Bookmarks, in this order. Each button SHALL do what its command does.

#### Scenario: Buttons in the title

- **WHEN** the Explorer shows the view Documentation Bookmarks
- **THEN** its title has the buttons Show Documentation Viewer, New Documentation Viewer and Reset Documentation Bookmarks, in this order

#### Scenario: Show from the view

- **WHEN** a viewer that shows `XML` is hidden behind a `.robot` file in its editor group, and the user clicks Show Documentation Viewer in the title of the view
- **THEN** the viewer that shows `XML` is the active editor of its group and has the focus

#### Scenario: New viewer from the view

- **WHEN** a viewer shows `Collections`, and the user clicks New Documentation Viewer in the title of the view
- **THEN** a new viewer shows `BuiltIn`, its target field has the focus with its text selected, and the first viewer still shows `Collections`
