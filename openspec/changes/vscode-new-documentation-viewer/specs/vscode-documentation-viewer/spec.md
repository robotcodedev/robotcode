## RENAMED Requirements

- FROM: `### Requirement: The command Open Documentation Viewer`
- TO: `### Requirement: The command New Documentation Viewer`

- FROM: `### Requirement: The command Open Documentation Viewer in New Window`
- TO: `### Requirement: The command Copy Documentation Viewer into New Window`

## MODIFIED Requirements

### Requirement: Documentation viewers are editor tabs

A Documentation Viewer SHALL be an editor tab that shows the documentation of one library, resource file or suite file, titled with its name. Several viewers SHALL be possible at the same time. Like an editor, a viewer SHALL be movable into other editor groups and into a window of its own, and SHALL be pinnable.

#### Scenario: Open Documentation Viewer
- **WHEN** the user runs "RobotCode: New Documentation Viewer" while a file of a workspace folder is the active editor
- **THEN** a new viewer shows `BuiltIn` of that folder, and the target field has the focus with its text selected

#### Scenario: Several viewers
- **WHEN** the user opens one viewer on `Collections` and another on `XML`
- **THEN** both tabs show their documentation, titled `Collections` and `XML`

#### Scenario: Hidden and shown again
- **WHEN** a viewer shows `Collections` at `Remove From List` with the filter `list`, and the user switches to another editor tab in the same group and back
- **THEN** the viewer shows `Collections` at the same position with the filter `list`, and back works as before

#### Scenario: Moved into a new window
- **WHEN** a viewer that shows `Collections` at `Remove From List` is moved with VS Code's "Move Editor into New Window"
- **THEN** it shows `Collections` at `Remove From List` in the new window, and back and forward work as before

#### Scenario: Reload of the window
- **WHEN** the window is reloaded while a viewer shows `XML`
- **THEN** the viewer shows `XML` at the same position again when its tab is shown

#### Scenario: New window from an active viewer
- **WHEN** the user runs "Copy Documentation Viewer into New Window" while a viewer that shows `BuiltIn` is active
- **THEN** a new window opens with a second viewer that shows `BuiltIn`, and the first viewer stays

### Requirement: The command New Documentation Viewer

The command "RobotCode: New Documentation Viewer" SHALL open a new viewer on `BuiltIn` of the workspace folder, with the target field focused and its text selected. The workspace folder is the one of the active editor. Without an active editor in a folder, the only folder is used; with several folders, the user SHALL choose one. Without a workspace folder, the commands SHALL show an error message.

#### Scenario: Several folders without an active editor
- **WHEN** a workspace has two folders, no editor is active, and the user runs "RobotCode: New Documentation Viewer"
- **THEN** the user is asked to choose one of the two folders

### Requirement: The command Copy Documentation Viewer into New Window

The command "RobotCode: Copy Documentation Viewer into New Window" SHALL open a new viewer in a new window. It SHALL show the target of the active viewer, or else of the viewer used last; without any viewer it SHALL show `BuiltIn`.

Both commands SHALL be in the command palette. The second command SHALL also be in the context menu of the active viewer's tab.

#### Scenario: New window without a viewer
- **WHEN** no viewer is open and the user runs "RobotCode: Copy Documentation Viewer into New Window"
- **THEN** a new window opens with a viewer that shows `BuiltIn`

### Requirement: Outline of new viewers

The setting `robotcode.documentationViewer.showOutline` SHALL decide whether a new viewer starts with its outline shown, and SHALL be `true` by default. A viewer restored from a state that does not record whether its outline is shown SHALL start as the setting says. A change of the setting SHALL NOT show or hide the outline of an open viewer.

#### Scenario: New viewer
- **WHEN** the user opens a new viewer while another viewer has its outline hidden
- **THEN** the new viewer shows its outline

#### Scenario: New viewer without the outline
- **WHEN** `robotcode.documentationViewer.showOutline` is `false` and the user runs "RobotCode: New Documentation Viewer"
- **THEN** the new viewer shows `BuiltIn` with its outline hidden, and the outline button shows the outline when clicked

#### Scenario: Setting changed while a viewer is open
- **WHEN** a viewer shows its outline and the user sets `robotcode.documentationViewer.showOutline` to `false`
- **THEN** that viewer keeps its outline, and the next new viewer starts without it

## ADDED Requirements

### Requirement: The button New Documentation Viewer

The toolbar of a viewer SHALL have the button "New Documentation Viewer", after the pin button. Choosing it SHALL open a new viewer on `BuiltIn` of the viewer's workspace folder, without asking for a folder, with the target field focused and its text selected. The new viewer SHALL open where the requirement "Where a viewer opens" says, and take the focus. The viewer whose button was chosen SHALL keep its target, position and history.

#### Scenario: Second viewer from the toolbar
- **WHEN** a viewer shows `Collections` at `Remove From List` and the user clicks "New Documentation Viewer" in its toolbar
- **THEN** a new viewer opens beside it and shows `BuiltIn`, its target field has the focus with its text selected, and the first viewer still shows `Collections` at `Remove From List`

#### Scenario: Folder of the viewer
- **WHEN** a workspace has the folders `tests` and `shared`, a viewer of `shared` shows `Collections`, and the user clicks "New Documentation Viewer" in its toolbar
- **THEN** the new viewer shows `BuiltIn` of `shared`, and the user is not asked for a folder

#### Scenario: New viewer in the active group
- **WHEN** `robotcode.documentationViewer.openLocation` is `active` and the user clicks "New Documentation Viewer" in the toolbar of a viewer
- **THEN** the new viewer opens in the editor group of that viewer

#### Scenario: Pinned viewer stays pinned
- **WHEN** a pinned viewer shows `XML` and the user clicks "New Documentation Viewer" in its toolbar
- **THEN** the new viewer is not pinned, and a following "Show in Documentation Viewer" still uses the viewer that shows `XML`
