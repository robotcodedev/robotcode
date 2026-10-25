## RENAMED Requirements

- FROM: `### Requirement: No suggestions without a language server`
- TO: `### Requirement: Only bookmarks without a language server`

## ADDED Requirements

### Requirement: The place in the target field

While a viewer shows the page of its target, the target field SHALL show after the target a `#` and the id of the heading at the top of the view, as `Collections#get-from-dictionary`, and the target alone at the top of the page. Entering a text with `#` SHALL show its target at the place after the last `#`: the heading with that id, else the keyword or data type with that name, else the top of the page. A target with a `#` of its own SHALL be entered and shown with a `#` at its end.

#### Scenario: Scrolled to a keyword

- **WHEN** a viewer shows `Collections`, and the user scrolls until `Get From Dictionary` is at the top of the view
- **THEN** the target field shows `Collections#get-from-dictionary`

#### Scenario: Top of the page

- **WHEN** a viewer shows the top of the page of `Collections`
- **THEN** the target field shows `Collections`

#### Scenario: Entering a place

- **WHEN** the user enters `Collections#get-from-list`
- **THEN** the viewer shows `Collections` with `Get From List` at the top of the view

#### Scenario: A keyword by its name

- **WHEN** the user enters `BuiltIn#Should Be Equal`
- **THEN** the viewer shows `BuiltIn` at `Should Be Equal`, and the target field shows `BuiltIn#should-be-equal`

#### Scenario: Another place of the target shown

- **WHEN** the target field shows `Collections#get-from-dictionary`, and the user enters `Collections#get-from-list`
- **THEN** the viewer shows `Get From List`, and back returns to `Get From Dictionary`

#### Scenario: The place that is shown

- **WHEN** the target field shows `Collections#get-from-dictionary`, and the user presses Enter in it
- **THEN** the viewer generates `Collections` again and stays at `Get From Dictionary`

#### Scenario: A target with a `#` of its own

- **WHEN** the workspace folder contains `issue#1/shop.resource`, and the user enters `issue#1/shop.resource#`
- **THEN** the viewer shows `issue#1/shop.resource` from the top of its page, and the target field shows `issue#1/shop.resource#`

#### Scenario: While typing

- **WHEN** the user has typed in the target field, and the page scrolls
- **THEN** the target field keeps the typed text

### Requirement: Scrolling past the end of a page

A viewer's page SHALL scroll past its end, as VS Code's editor scrolls beyond its last line, so that every heading of the page can come to the top of the view, also the last ones of a page.

#### Scenario: Last keyword of a library

- **WHEN** the user enters `Collections#sort-list`, the last keyword of `Collections`
- **THEN** the viewer shows `Sort List` at the top of the view, and the target field shows `Collections#sort-list`

#### Scenario: A short page

- **WHEN** a resource file has one keyword, and a viewer shows the file at that keyword
- **THEN** the keyword is at the top of the view, and the star bookmarks it

### Requirement: Bookmarks of places in a viewer

The toolbar of a viewer SHALL have a star button that bookmarks the place the viewer shows in the viewer's workspace folder: its target as the target field shows it before a `#`, and the heading at the top of the view, or the target alone at the top of the page. The star SHALL show whether the place is bookmarked for the folder, and a click on it SHALL remove the bookmark of a bookmarked place. A target MAY have several bookmarks. Bookmarks SHALL be kept across restarts of VS Code.

#### Scenario: Bookmark a keyword

- **WHEN** a viewer shows `Collections` with the keyword `Get From Dictionary` at the top of the view, and the user clicks the star
- **THEN** the star is filled, and the bookmark `Collections › Get From Dictionary` exists in the viewer's workspace folder

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

- **WHEN** a viewer has bookmarked `Collections › Get From Dictionary`, and another viewer of the same workspace folder shows that place
- **THEN** the star of the other viewer is filled as well

#### Scenario: After a restart

- **WHEN** the bookmark `Collections › Get From Dictionary` exists, and VS Code is restarted
- **THEN** the suggestion list and the view Documentation Bookmarks still offer the bookmark

#### Scenario: No page

- **WHEN** a viewer shows no page, as after a target that fails
- **THEN** its star cannot be clicked

### Requirement: Where a bookmark holds

A bookmark SHALL first belong to the workspace folder of the viewer that set it, and hold only for that folder. A bookmark that the user has moved to All Workspaces SHALL hold in all workspaces. Where a bookmark holds SHALL NOT depend on its target.

#### Scenario: A bookmark of the folder

- **WHEN** a workspace has the folders `tests` and `shared`, and a viewer of `shared` has bookmarked `ShopLibrary`
- **THEN** the suggestion list of a viewer of `tests` does not offer that bookmark, and the view lists it in the group `shared`

#### Scenario: In All Workspaces

- **WHEN** the user has moved the bookmark `Collections › Get From Dictionary` to All Workspaces and opens another workspace
- **THEN** the view Documentation Bookmarks and the suggestion list of a viewer there offer the bookmark

### Requirement: Bookmarks with Settings Sync

The bookmarks of All Workspaces SHALL be part of the extension state that VS Code's Settings Sync takes to the other machines of the user while it syncs extensions. The bookmarks of workspace folders SHALL NOT, since they belong to a workspace on one machine.

#### Scenario: Another machine

- **WHEN** Settings Sync syncs extensions on two machines with the same version of RobotCode, and the user moves the bookmark `Collections › Get From Dictionary` to All Workspaces on one of them
- **THEN** the other machine offers that bookmark after its next sync

### Requirement: Bookmarks in the suggestion list

The suggestion list SHALL offer the bookmarks that hold for the viewer's folder before the completion: all of them for an empty field, else those whose label or text in the target field contains the typed text, without regard to case. A bookmark's label SHALL be its target and the title of its heading, as `Collections › Get From Dictionary`, sorted by label. Enter and a click SHALL open its target at its heading; Tab SHALL put its target and place into the field.

#### Scenario: Down in an empty field

- **WHEN** the bookmarks `Collections › Get From Dictionary` and `XML` exist, and the user clears the target field and presses Down
- **THEN** the list offers both bookmarks, `Collections › Get From Dictionary` first

#### Scenario: Typed text in the heading

- **WHEN** the bookmark `Collections › Get From Dictionary` exists, and the user types `dict`
- **THEN** the list offers that bookmark

#### Scenario: Bookmark before the completion

- **WHEN** the bookmark `Collections › Get From Dictionary` exists, and the user types `Coll`
- **THEN** the list offers the bookmarks that contain `Coll` first, the first of them selected, then the completion `Collections`

#### Scenario: Bookmark selected before the completion

- **WHEN** the bookmarks `Collections` and `Dialogs` exist, and the user types `o`, presses Down at once and waits for the completion
- **THEN** `Dialogs` stays selected

#### Scenario: Open a bookmark

- **WHEN** the list offers the bookmark `Collections › Get From Dictionary`, and the user presses Enter on it
- **THEN** the viewer shows `Collections` with `Get From Dictionary` at the top of the view

#### Scenario: Tab on a bookmark

- **WHEN** the list offers the bookmark `Collections › Get From Dictionary` selected, and the user presses Tab
- **THEN** the field holds `Collections#get-from-dictionary`, the list is closed, and the viewer still shows the page it showed before

#### Scenario: Bookmark with import arguments

- **WHEN** the bookmark `ArgLib::b` exists, and the user types `ArgLib::`
- **THEN** the list offers the bookmark `ArgLib::b`, although a text with `::` gets no completion

### Requirement: Removing a bookmark in the list

A bookmark in the suggestion list SHALL show a remove button while the mouse rests on it and while it is selected. A click on that button SHALL remove the bookmark from the viewer's folder and from All Workspaces, and the list SHALL stay open with the remaining suggestions.

#### Scenario: Remove in the list

- **WHEN** the list offers the bookmarks `Collections › Get From Dictionary` and `XML`, and the user clicks the remove button of `XML`
- **THEN** the bookmark `XML` is gone, and the list still offers `Collections › Get From Dictionary`

#### Scenario: Star of a viewer at the removed place

- **WHEN** a viewer shows the place of the bookmark `XML`, and the user removes that bookmark in the list of another viewer
- **THEN** the star of the first viewer is empty

### Requirement: The view Documentation Bookmarks

The Explorer SHALL have a view Documentation Bookmarks while a Robot Framework file or a Documentation Viewer is the active editor. While a bookmark exists, it SHALL list the group All Workspaces and a group for each workspace folder, each sorted by label. A click on a bookmark SHALL open it as the actions of the editor open documentation (requirement "Which viewer shows documentation from the editor"), and an inline action SHALL remove it from its group.

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

- **WHEN** the workspace has the folders `tests` and `shared`, and only All Workspaces has bookmarks
- **THEN** the view has the groups All Workspaces, `tests` and `shared`

#### Scenario: Without bookmarks

- **WHEN** no bookmark exists
- **THEN** the view says how the star of a viewer adds one

### Requirement: Moving a bookmark

In the view Documentation Bookmarks, the context menu of a bookmark SHALL move it to All Workspaces or to a workspace folder, and dragging a bookmark onto a group or onto a bookmark of a group SHALL move it into that group. Moving to a workspace folder SHALL ask for the folder when there is more than one to choose from. A bookmark that the target group has already SHALL be there once.

#### Scenario: Move to All Workspaces

- **WHEN** the bookmark `Collections › Get From Dictionary` is in the group of the folder `robotcode-demo`, and the user chooses Move to All Workspaces in its context menu
- **THEN** the bookmark is in All Workspaces and no longer in `robotcode-demo`

#### Scenario: Move to the workspace folder

- **WHEN** the workspace has one folder, and the user chooses Move to Workspace Folder in the context menu of a bookmark of All Workspaces
- **THEN** the bookmark is in the group of that folder and no longer in All Workspaces

#### Scenario: Several workspace folders

- **WHEN** the workspace has the folders `tests` and `shared`, and the user chooses Move to Workspace Folder in the context menu of a bookmark of All Workspaces
- **THEN** VS Code asks for the folder, and the bookmark moves into the chosen one

#### Scenario: Drag and drop

- **WHEN** the user drags a bookmark of the group `tests` onto the group `shared`
- **THEN** the bookmark is in `shared` and no longer in `tests`

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

### Requirement: The target field

The toolbar of a viewer SHALL have a target field. It SHALL show what the viewer documents, as `Name`, `Name::arg1::arg2` or the path of a library, resource or suite file, relative to the viewer's workspace folder or absolute, followed by the place it shows (requirement "The place in the target field"). Entering another target SHALL show its documentation in the same tab, which takes the new name as its title. Entering the target and the place that are shown SHALL refresh them.

#### Scenario: Another target
- **WHEN** the user enters `Collections` in the target field of a viewer that shows `BuiltIn`
- **THEN** the viewer shows `Collections`, titled `Collections`, and back returns to `BuiltIn`

#### Scenario: Import arguments
- **WHEN** a library `ArgLib` offers the keyword `Mode B Keyword` only when it is initialised with `b`, and the user enters `ArgLib::b`
- **THEN** the page and the outline list `Mode B Keyword`

#### Scenario: Target that fails
- **WHEN** the user enters the name of a library that does not exist
- **THEN** the page area shows the error and a retry button, the field keeps the entered name, and back returns to the previous page

#### Scenario: Target that starts with a dash
- **WHEN** the workspace folder contains the resource file `-shared.resource`, and the user enters `-shared.resource`
- **THEN** the viewer shows the keywords of that file

### Requirement: Back, forward and find

A viewer SHALL keep a history of what it showed. Choosing an outline entry, following a link within the page, entering a target, picking another workspace folder, and documentation shown by an action from the editor or the Keywords view SHALL each add an entry. Entering the target and place shown SHALL only refresh them; another place of that target SHALL add an entry. Choosing the outline entry, or following a link, to the heading the current entry shows SHALL only show that heading again.

#### Scenario: Back with the keyboard
- **WHEN** the user follows the link `Should Be Equal` in the introduction of `BuiltIn` and then presses Alt+Left in the viewer
- **THEN** the page returns to the introduction, and VS Code's own Go Back does not run

#### Scenario: Mouse back button
- **WHEN** the user presses the mouse's back button over the page
- **THEN** the viewer goes back

#### Scenario: Find in the page
- **WHEN** the user presses Ctrl+F in a viewer that shows `BuiltIn` and types `Should Be Equal`
- **THEN** the find bar shows the number of matches in the page, without the entries of the outline
- **AND** Enter scrolls the page to the next match

#### Scenario: Phrase across a line break
- **WHEN** the user searches `automatically and thus` in a viewer that shows `BuiltIn` on Robot Framework 7.5, whose documentation breaks the line between `and` and `thus`
- **THEN** the find bar shows a match

#### Scenario: Find bar open during a show
- **WHEN** the find bar of a viewer that shows `BuiltIn` is open with `list`, and the user chooses "Show in Documentation Viewer" on a call of `Append To List`
- **THEN** the viewer shows `Collections` at `Append To List`

#### Scenario: Same heading again
- **WHEN** the page shows `Should Be Equal` after the user chose it in the outline, and the user chooses it again
- **THEN** no history entry is added, and back returns to the entry before it

### Requirement: Documentation actions document the import the analysis used

The documentation actions of the editor and the Keywords view, and the links of a hover, SHALL document the import through which the analysis resolved the name at the cursor:
- Variables in the import name and arguments SHALL be replaced with the values the analysis knows; the arguments SHALL be passed as strings.
- A library imported by module name, such as `BuiltIn` or `Collections`, SHALL be shown with the same target wherever it was shown from.

#### Scenario: Library whose arguments fail
- **WHEN** a suite imports `alibrary` with `port=80x`, and `port` of `alibrary` takes an integer, so the analysis loads `alibrary` without arguments
- **AND** the user clicks the link to `A Library Keyword` in the hover of the import, or chooses "Show in Documentation Viewer" on the import
- **THEN** the viewer's target field shows `alibrary` without arguments, with `#a-library-keyword` after it for the link, and the viewer shows its page instead of the error of `alibrary::port=80x`

#### Scenario: Resource imported through a resource in another directory
- **WHEN** a suite imports `sub/local.resource`, which imports `deeper/nested.resource`, and documentation is opened on a call of a keyword of `nested.resource` in the suite
- **THEN** "Open Documentation (deprecated)" and the Documentation Viewer both show `nested.resource`
- **AND** the viewer's target field shows the path of `nested.resource` relative to the workspace folder, followed by `#` and the id of the keyword

#### Scenario: Second import of the same library
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello` and with `a_param=${LIB_ARG}` as `lib_var`, `${LIB_ARG}` is `from lib`, and documentation is opened on `lib_var.A Library Keyword`
- **THEN** the viewer's target field shows `alibrary::a_param=from lib#a-library-keyword`, and the URL of "Open Documentation (deprecated)" carries `a_param=from lib`
- **AND** on `lib_hello.A Library Keyword` they carry `a_param=from hello`, also when the analysis of the suite was restored from the cache

#### Scenario: Call without a prefix decided by the search order
- **WHEN** a suite imports `alibrary` as `lib_hello` and as `lib_var` as above, `robotcode.analysis.robot.globalLibrarySearchOrder` is `["lib_var"]`, and documentation is opened on a call of `A Library Keyword` without a prefix
- **THEN** the viewer's target field shows `alibrary::a_param=from lib#a-library-keyword`, and the URL of "Open Documentation (deprecated)" carries `a_param=from lib`, also when the analysis of the suite was restored from the cache

#### Scenario: Module library from two directories
- **WHEN** the user chooses "Show in Documentation Viewer" on `Library    Collections` in two suites in different directories
- **THEN** the viewer's target field shows `Collections` both times

#### Scenario: Hover link on the second import
- **WHEN** the suite above is open and the user clicks the heading of the hover on `lib_var.A Library Keyword`
- **THEN** the viewer's target field shows `alibrary::a_param=from lib#a-library-keyword`, also when the analysis of the suite was restored from the cache

### Requirement: Documented import of a call with a prefix

For a keyword call with a library or resource prefix (`lib_var.A Library Keyword`), the documentation actions SHALL document the import the prefix names. When the same library is imported twice with different arguments, a call through the second import's alias SHALL use the second import's arguments.

#### Scenario: First import of the same library
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello` and with `a_param=from lib` as `lib_var`, and the user chooses "Show in Documentation Viewer" on `lib_hello.A Library Keyword`
- **THEN** the viewer's target field shows `alibrary::a_param=from hello#a-library-keyword`

### Requirement: Documented import of a call without a prefix

For a keyword call without a prefix, the documentation actions SHALL document the import the analysis resolved the call to, also when the same library is imported twice with different arguments and the library search order or the keywords of the two imports decide.

#### Scenario: Search order naming the first import
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello` and with `a_param=from lib` as `lib_var`, `robotcode.analysis.robot.globalLibrarySearchOrder` is `["lib_hello"]`, and documentation is opened on a call of `A Library Keyword` without a prefix
- **THEN** the viewer's target field shows `alibrary::a_param=from hello#a-library-keyword`

### Requirement: Documented library loaded without the import's arguments

A library that the analysis loaded without the import's arguments, because loading it with them failed, SHALL be shown by the documentation actions without arguments, as hover, completion and signature help show it.

#### Scenario: Keyword of a library whose arguments fail
- **WHEN** a suite imports `alibrary` with `port=80x`, which the analysis loads without arguments, and the user chooses "Show in Documentation Viewer" on a call of `A Library Keyword`
- **THEN** the viewer's target field shows `alibrary#a-library-keyword`, without arguments
