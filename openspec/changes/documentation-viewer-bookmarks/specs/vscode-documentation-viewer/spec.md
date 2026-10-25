## RENAMED Requirements

- FROM: `### Requirement: No suggestions without a language server`
- TO: `### Requirement: Only bookmarks without a language server`

## ADDED Requirements

### Requirement: Bookmarks of places in a viewer

The toolbar of a viewer SHALL have a star button that bookmarks the place the viewer shows: its target as the target field shows it, and the heading at the top of the view, or the target alone at the top of the page. The star SHALL show whether the place is bookmarked, and a click on it SHALL remove the bookmark of a bookmarked place. A target MAY have several bookmarks. Bookmarks SHALL be shared by all viewers and kept across restarts of VS Code.

#### Scenario: Bookmark a keyword

- **WHEN** a viewer shows `Collections` with the keyword `Get From Dictionary` at the top of the view, and the user clicks the star
- **THEN** the star is filled, and the bookmark `Collections › Get From Dictionary` exists

#### Scenario: Top of the page

- **WHEN** a viewer shows the top of the page of `Collections`, and the user clicks the star
- **THEN** the bookmark `Collections` exists, which holds no heading

#### Scenario: Several places of a target

- **WHEN** the bookmark `Collections › Get From Dictionary` exists, and the user scrolls to `Get From List` and clicks the star
- **THEN** both bookmarks exist, and the star is filled at each of the two places and empty elsewhere

#### Scenario: Remove with the star

- **WHEN** a viewer shows the place of the bookmark `Collections › Get From Dictionary`, and the user clicks the filled star
- **THEN** the bookmark is gone and the star is empty

#### Scenario: Another viewer

- **WHEN** a viewer has bookmarked `Collections › Get From Dictionary`, and another viewer shows that place
- **THEN** the star of the other viewer is filled as well

#### Scenario: After a restart

- **WHEN** the bookmark `Collections › Get From Dictionary` exists, and VS Code is restarted
- **THEN** the suggestion list and the view Documentation Bookmarks still offer the bookmark

#### Scenario: No page

- **WHEN** a viewer shows no page, as after a target that fails
- **THEN** its star cannot be clicked

### Requirement: Where a bookmark holds

A bookmark of a target by name, such as `Collections` or `Browser`, SHALL hold in all workspaces. A bookmark of a file SHALL belong to the workspace folder of the viewer that set it. A target is a file when its name, the text before the first `::`, contains a path separator or ends with the extension of a library, resource or suite file or of a Libdoc spec file.

#### Scenario: A name in another workspace

- **WHEN** the user has bookmarked `Collections › Get From Dictionary` in one workspace and opens another workspace
- **THEN** the view Documentation Bookmarks and the suggestion list of a viewer there offer the bookmark

#### Scenario: A file in another workspace folder

- **WHEN** a workspace has the folders `tests` and `shared`, and a viewer of `shared` has bookmarked `common.resource`
- **THEN** the suggestion list of a viewer of `tests` does not offer that bookmark, and the view lists it in the group `shared`

### Requirement: Bookmarks with Settings Sync

The bookmarks that hold in all workspaces SHALL be part of the extension state that VS Code's Settings Sync takes to the other machines of the user while it syncs extensions. The bookmarks of files SHALL NOT, since their paths belong to a workspace on one machine.

#### Scenario: Another machine

- **WHEN** Settings Sync syncs extensions on two machines with the same version of RobotCode, and the user bookmarks `XML` on one of them
- **THEN** the other machine offers the bookmark `XML` after its next sync

### Requirement: Bookmarks in the suggestion list

The suggestion list SHALL offer the bookmarks that hold for the viewer's folder before the completion: all of them for an empty field, else those whose label contains the typed text without regard to case. A bookmark's label SHALL be its target and the title of its heading, as `Collections › Get From Dictionary`, and the bookmarks SHALL be sorted by label. Enter and a click SHALL open its target at its heading; Tab SHALL put its target into the target field.

#### Scenario: Down in an empty field

- **WHEN** the bookmarks `Collections › Get From Dictionary` and `XML` exist, and the user clears the target field and presses Down
- **THEN** the list offers both bookmarks, `Collections › Get From Dictionary` first

#### Scenario: Typed text in the heading

- **WHEN** the bookmark `Collections › Get From Dictionary` exists, and the user types `dict`
- **THEN** the list offers that bookmark

#### Scenario: Bookmark before the completion

- **WHEN** the bookmark `Collections › Get From Dictionary` exists, and the user types `Coll`
- **THEN** the list offers the bookmarks that contain `Coll` first, the first of them selected, then the completion `Collections`

#### Scenario: Open a bookmark

- **WHEN** the list offers the bookmark `Collections › Get From Dictionary`, and the user presses Enter on it
- **THEN** the viewer shows `Collections` with `Get From Dictionary` at the top of the view

#### Scenario: Tab on a bookmark

- **WHEN** the list offers the bookmark `Collections › Get From Dictionary` selected, and the user presses Tab
- **THEN** the field holds `Collections`, the list is closed, and the viewer still shows the page it showed before

#### Scenario: Bookmark with import arguments

- **WHEN** the bookmark `ArgLib::b` exists, and the user types `ArgLib::`
- **THEN** the list offers the bookmark `ArgLib::b`, although a text with `::` gets no completion

### Requirement: Removing a bookmark in the list

A bookmark in the suggestion list SHALL show a remove button while the mouse rests on it and while it is selected. A click on that button SHALL remove the bookmark, and the list SHALL stay open with the remaining suggestions.

#### Scenario: Remove in the list

- **WHEN** the list offers the bookmarks `Collections › Get From Dictionary` and `XML`, and the user clicks the remove button of `XML`
- **THEN** the bookmark `XML` is gone, and the list still offers `Collections › Get From Dictionary`

#### Scenario: Star of a viewer at the removed place

- **WHEN** a viewer shows the place of the bookmark `XML`, and the user removes that bookmark in the list of another viewer
- **THEN** the star of the first viewer is empty

### Requirement: The view Documentation Bookmarks

The Explorer SHALL have a view Documentation Bookmarks while a Robot Framework file or a Documentation Viewer is the active editor. It SHALL list the bookmarks in a group All Workspaces and in one group for each workspace folder with bookmarks, each sorted by label. A click on a bookmark SHALL open it as the actions of the editor open documentation (requirement "Which viewer shows documentation from the editor"), and an inline action SHALL remove it.

#### Scenario: With a Robot Framework file

- **WHEN** a `.robot` file is the active editor
- **THEN** the Explorer shows the view Documentation Bookmarks

#### Scenario: With a Documentation Viewer

- **WHEN** a Documentation Viewer is the active editor
- **THEN** the Explorer shows the view Documentation Bookmarks

#### Scenario: With another editor

- **WHEN** a Python file is the active editor
- **THEN** the Explorer does not show the view Documentation Bookmarks

#### Scenario: Open from the view

- **WHEN** a viewer is open, and the user clicks `Collections › Get From Dictionary` in the view
- **THEN** the viewer that actions from the editor use shows `Collections` with `Get From Dictionary` at the top of the view

#### Scenario: Without a viewer

- **WHEN** no viewer is open, and the user clicks `XML` in the view
- **THEN** a new viewer shows `XML`

#### Scenario: Remove in the view

- **WHEN** the user removes `XML` with its inline action in the view
- **THEN** the view, the suggestion lists and the stars no longer show the bookmark `XML`

#### Scenario: Groups

- **WHEN** the workspace has the folders `tests` and `shared`, the bookmark `XML` exists, and both folders have bookmarks of files
- **THEN** the view has the groups All Workspaces, `tests` and `shared`, and `XML` is in All Workspaces

### Requirement: Default bookmarks

When RobotCode starts for the first time, it SHALL bookmark the standard libraries `BuiltIn`, `Collections`, `DateTime`, `Dialogs`, `OperatingSystem`, `Process`, `Remote`, `Screenshot`, `String`, `Telnet` and `XML` in All Workspaces, each without a heading. They SHALL be bookmarks like the others, so that a removed one does not come back, also not on another machine that gets the bookmarks through Settings Sync.

#### Scenario: First start

- **WHEN** RobotCode starts for the first time
- **THEN** the view Documentation Bookmarks lists the eleven standard libraries in the group All Workspaces

#### Scenario: A removed default bookmark

- **WHEN** the user removes the bookmark `Telnet` and restarts VS Code
- **THEN** the bookmark `Telnet` stays removed

### Requirement: Resetting the bookmarks

The command RobotCode: Reset Documentation Bookmarks, also an action in the title of the view Documentation Bookmarks, SHALL ask for a confirmation. After it, it SHALL remove the bookmarks of All Workspaces and of the workspace folders that are open, and bookmark the standard libraries of the requirement "Default bookmarks" again.

#### Scenario: Reset

- **WHEN** the user has bookmarked `Collections › Get From Dictionary` and removed `Telnet`, runs the command and confirms
- **THEN** the view lists the eleven standard libraries only

#### Scenario: Cancel

- **WHEN** the user runs the command and does not confirm
- **THEN** the bookmarks stay as they were

## MODIFIED Requirements

### Requirement: Suggestions under the target field

While the target field has the focus, the viewer SHALL show a list of suggestions under it when the user types, presses Ctrl+Space, on macOS also Option+Escape, or presses Down: the matching bookmarks, then the completion of the name, and all bookmarks for an empty field. Without a suggestion, the list SHALL stay closed. It SHALL close on Escape, also before it appears, when the field loses the focus, when a target loads, and when the viewer goes to another entry.

#### Scenario: Typing a name

- **WHEN** the user types `Coll` in the target field
- **THEN** a list under the field offers `Collections`

#### Scenario: Ctrl+Space

- **WHEN** the user has typed `Coll` and closed the list with Escape, and presses Ctrl+Space
- **THEN** the list offers `Collections` again

#### Scenario: Option+Escape on macOS

- **WHEN** on macOS the user has typed `Coll` and closed the list with Escape, and presses Option+Escape
- **THEN** the list offers `Collections` again

#### Scenario: Down

- **WHEN** the field holds `XM`, the list is closed, and the user presses Down
- **THEN** the list offers `XML`

#### Scenario: Empty field

- **WHEN** no bookmark holds for the viewer's folder, and the user clears the target field and presses Down
- **THEN** no list opens

#### Scenario: Escape

- **WHEN** the list is open and the user presses Escape
- **THEN** the list closes and the field keeps the typed text

#### Scenario: Escape before the list appears

- **WHEN** the user types `Coll` and presses Escape before the list appears
- **THEN** no list opens, and Enter then loads `Coll` as typed

#### Scenario: Back to the same page

- **WHEN** a viewer has gone from `BuiltIn` to a heading of `BuiltIn`, the list is open for `resources/sh`, and the user goes back
- **THEN** the list closes and the field holds `BuiltIn`

### Requirement: Order of the suggestions

The list SHALL order its completions as the editor's completion does: first the names that continue the typed part in the same case, then the others, each alphabetically without regard to case. Of two equal names, a module SHALL come before a file, and a file before a directory. The bookmarks SHALL come before the completions.

#### Scenario: Typed with a capital letter

- **WHEN** no bookmark contains `Coll`, and the user types `Coll`
- **THEN** the list offers `Collections` first, then `collections` as a module, then `collections` as a directory

#### Scenario: Typed in small letters

- **WHEN** no bookmark contains `xml`, and the user types `xml`
- **THEN** the list offers `xml` as a module first, then `xml` as a directory, and `XML` only after the names that start with `xml`

### Requirement: Only bookmarks without a language server

While no language server of RobotCode runs for the viewer's workspace folder, the list SHALL offer only the bookmarks, and the viewer SHALL NOT start a language server for it. This holds while the folder's Python environment is not usable yet and when RobotCode is switched off for the folder.

#### Scenario: Environment without Robot Framework

- **WHEN** the Python environment of the folder has no Robot Framework, the bookmark `Collections` exists, and the user types `Coll`
- **THEN** the list offers only the bookmarks that contain `Coll`, such as `Collections`

### Requirement: The suggestion list for screen readers

Screen readers SHALL announce the target field as a combobox that controls the list, the list as a list of suggestions, and the selected suggestion with its kind, such as a bookmark, a module, a file or a directory.

#### Scenario: Selected suggestion

- **WHEN** no bookmark contains `Coll`, and the user types `Coll` and the list opens
- **THEN** the accessibility tree has the target field as an expanded combobox whose active descendant is the option `Collections`, with its kind
