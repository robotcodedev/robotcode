# Spec: vscode-documentation-viewer

## Purpose

Defines the Documentation Viewer of the VS Code extension and how RobotCode opens documentation from the editor:
- the viewers and how the user arranges them;
- the workspace folder of a viewer;
- the target field, and the page with its outline;
- navigation and find;
- how pages are generated, kept and refreshed;
- which viewer an action uses;
- the documentation actions of the editor and the Keywords view, and the import these actions document;
- where Libdoc pages open.

## Requirements

### Requirement: Documentation actions in the editor

RobotCode SHALL offer the source actions "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Open Documentation (deprecated)", in this order, under the same conditions:
- on the name of a Library or Resource import;
- on a keyword reference in a keyword call, setup, teardown or template;
- on the name in a keyword definition header.

The offered actions and what they document SHALL be the same whether the semantic-model analysis path is enabled or not.

#### Scenario: Library import name
- **WHEN** source actions are requested with the cursor on `Collections` in `Library    Collections`
- **THEN** the menu lists "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Open Documentation (deprecated)", in this order, all for the library `Collections`

#### Scenario: Keyword of a library
- **WHEN** the user chooses "Show in Documentation Viewer" on a call of `Remove From List`
- **THEN** a viewer shows `Collections` at `Remove From List`

#### Scenario: Keyword definition in a resource file
- **WHEN** source actions are requested on the name in a keyword definition header of a `.resource` file
- **THEN** the three actions are offered, and "Show in Documentation Viewer" shows that resource file at the keyword

#### Scenario: Keyword definition in a suite file
- **WHEN** source actions are requested on the name in a keyword definition header of a file with a `*** Test Cases ***` section
- **THEN** the three actions are offered, and "Show in Documentation Viewer" shows that suite file at the keyword

#### Scenario: Both analysis paths
- **WHEN** the same positions are evaluated with the semantic-model analysis path enabled and disabled
- **THEN** the offered actions, their order and what they document are identical

#### Scenario: Deprecated action
- **WHEN** the user chooses "Open Documentation (deprecated)" on a call of `Remove From List`
- **THEN** the Libdoc page of `Collections` opens at `Remove From List`

#### Scenario: Own key on a keyword
- **WHEN** the user has bound a key to `editor.action.sourceAction` with the arguments `{"kind": "source", "preferred": true, "apply": "first"}`, the cursor is on a call of `Remove From List`, and the user presses that key
- **THEN** a viewer shows `Collections` at `Remove From List`, no menu is shown, and the editor keeps the focus

#### Scenario: Own key without documentation
- **WHEN** the cursor is in a comment and the user presses that key
- **THEN** no viewer opens or changes, and VS Code reports that no preferred source action is available

#### Scenario: No key of RobotCode
- **WHEN** the cursor is on a call of `Remove From List` and the user presses Shift+F1 without a binding of their own
- **THEN** no viewer opens

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

### Requirement: The Keywords view opens documentation at the keyword

Each import and keyword item of the Keywords view SHALL offer these actions, for the same import as the documentation actions of the editor:
- a book button titled "Show in Documentation Viewer", which SHALL do what "Show in Documentation Viewer" does.

Each of these actions on a keyword SHALL open the documentation at that keyword, also when the keyword is defined in the current document.

#### Scenario: Book button
- **WHEN** the user clicks the book button of the keyword `Remove From List` under the import `Collections` in the Keywords view
- **THEN** a viewer shows `Collections` at `Remove From List`

#### Scenario: Order of the context menu
- **WHEN** the user opens the context menu of an import or keyword item in the Keywords view
- **THEN** it lists "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Show Documentation (deprecated)", in this order

#### Scenario: Local keyword with "Show Documentation"
- **WHEN** the user chooses "Show Documentation (deprecated)" in the context menu of a keyword of the current file in the Keywords view
- **THEN** the Libdoc page opens at that keyword

#### Scenario: Local keyword with "Show in Documentation Viewer"
- **WHEN** the user chooses "Show in Documentation Viewer" on a keyword of the current file in the Keywords view
- **THEN** a viewer shows the current file at that keyword

#### Scenario: Library import item
- **WHEN** the user chooses "Show in Documentation Viewer" on the import item `lib_hello` of `alibrary`
- **THEN** a viewer shows `alibrary`, and its target field shows `alibrary::a_param=from hello`

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

### Requirement: The workspace folder of a viewer

Each viewer SHALL belong to one workspace folder. Its pages SHALL be generated for that folder, as the requirement "Pages are generated live and kept" describes.
- A viewer that shows documentation for an action of the editor or the Keywords view SHALL belong to the folder of the document the action came from, also when the documented file lies in another workspace folder.

#### Scenario: Folder in a multi-root workspace
- **WHEN** a workspace has the folders `tests` and `shared`, and a viewer of `tests` shows `Collections`
- **THEN** the toolbar shows `tests` before the pin button

#### Scenario: Picking another folder
- **WHEN** the user chooses the folder in the toolbar of that viewer and picks `shared`
- **THEN** the viewer shows `Collections`, generated with the Python environment, profiles and settings of `shared`, and the toolbar shows `shared`
- **AND** back shows `Collections` of `tests` again

#### Scenario: Documented file in another folder
- **WHEN** `tests/suite.robot` imports `../shared/common.resource`, and the user chooses "Show in Documentation Viewer" on a call of a keyword of `common.resource`
- **THEN** the viewer belongs to `tests` and shows `common.resource` at that keyword
- **AND** after the user enters `BuiltIn`, switches to another editor tab in the same group and back, the viewer still shows `BuiltIn`, and back returns to `common.resource`

#### Scenario: One folder
- **WHEN** the workspace has one folder
- **THEN** the toolbar of a viewer shows no folder

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

### Requirement: Which viewer shows documentation from the editor

"Show in Documentation Viewer" and the item action of the Keywords view SHALL choose the viewer in this order:
1. the viewer the user pinned with the viewer's pin button, if it is open;
2. otherwise the viewer used last: the one that was active last, or that such an action or a command opened or brought forward last, whichever happened later;
3. otherwise a new viewer.

#### Scenario: No viewer open
- **WHEN** no viewer is open and the user chooses "Show in Documentation Viewer" on `Collections`
- **THEN** a viewer opens beside the editor and shows `Collections`, and the focus stays in the editor

#### Scenario: Two actions in a row
- **WHEN** the user chooses "Show in Documentation Viewer" on `Collections` and then, without clicking into the viewer, on a call of `Log`
- **THEN** the same viewer shows `BuiltIn` at `Log`, and no second viewer opens

#### Scenario: Last active viewer
- **WHEN** two viewers are open, the user last worked in the one that shows `XML`, and then chooses "Show in Documentation Viewer" on a call of `Log`
- **THEN** that viewer shows `BuiltIn` at `Log`

#### Scenario: Pinned viewer
- **WHEN** two viewers are open, the one that shows `XML` is pinned, the user last worked in the other one, and then chooses "Show in Documentation Viewer" on a call of `Log`
- **THEN** the pinned viewer shows `BuiltIn` at `Log`, and the other viewer is unchanged

#### Scenario: New viewer in the active group
- **WHEN** `robotcode.documentationViewer.openLocation` is `active`, no viewer is open, and the user chooses "Show in Documentation Viewer"
- **THEN** the new viewer opens in the editor group of the active editor

#### Scenario: Viewer in another window
- **WHEN** the viewer that was active last was moved into a window of its own, and the user chooses "Show in Documentation Viewer" in the main window
- **THEN** that viewer shows the documentation, and its window comes to the front

#### Scenario: Show in a new viewer
- **WHEN** a pinned viewer shows `XML`, and the user chooses "Show in New Documentation Viewer" on `Library    Collections`
- **THEN** a new viewer opens beside the editor and shows `Collections`, the pinned viewer still shows `XML`, and a following "Show in Documentation Viewer" still uses the pinned viewer

### Requirement: Pages are generated live and kept

The page of a target SHALL be what `robotcode doc lib` produces for it, run in the Python environment that RobotCode uses for the viewer's workspace folder. It SHALL be run with:
- the folder's selected profiles;
- the folder's settings `robotcode.robot.pythonPath`, `robotcode.robot.languages`, `robotcode.robot.variables`, `robotcode.robot.variableFiles` and `robotcode.robot.env`.

#### Scenario: Kept page
- **WHEN** the user shows a target that was generated in an earlier session
- **THEN** the kept page is shown at once, and it is replaced when the new generation gives a different result

#### Scenario: Profile variable in the import arguments
- **WHEN** a library `ArgLib` offers the keyword `Mode B Keyword` only when it is initialised with `b`, the profile selected in `robotcode.profiles` sets the variable `MODE` to `b`, and the target `ArgLib::${MODE}` is shown
- **THEN** the page lists `Mode B Keyword`

#### Scenario: Another profile selected in the same session
- **WHEN** a viewer showed `ArgLib::${MODE}` while the selected profile set `MODE` to `a`, the user then selects a profile that sets `MODE` to `b`, and a viewer shows `ArgLib::${MODE}` again
- **THEN** the page lists `Mode B Keyword`

#### Scenario: Keyword added since the page was generated
- **WHEN** a resource file was shown in this session, the user then adds the keyword `New Keyword` to it and saves it, and chooses "Show in Documentation Viewer" on a call of `New Keyword`
- **THEN** the viewer shows the resource file at `New Keyword`

#### Scenario: Language from the settings
- **WHEN** `robotcode.robot.languages` is `["de"]`, `robot.toml` and the profiles set no languages, and the user shows a resource file with the headers `*** Einstellungen ***` and `*** Schlüsselwörter ***` and no `Language:` line, on Robot Framework 6.0 or newer
- **THEN** the page lists the keywords of the file

#### Scenario: Import arguments that fail
- **WHEN** the library of a target cannot be initialised with the target's arguments, and a page of the target was kept before
- **THEN** the viewer shows the error together with the kept page

#### Scenario: Markdown-documented library without Python-Markdown
- **WHEN** a viewer shows `BuiltIn` on Robot Framework 7.5 in an environment without the `markdown` package
- **THEN** the full documentation is shown

### Requirement: Libdoc pages open beside the editor

On desktop, "Open Documentation (deprecated)", "Show Documentation (deprecated)" of the Keywords view, and output files opened with `robotcode.run.openOutputTarget` set to `simpleBrowser`, SHALL open in VS Code's integrated browser beside the editor. A later page SHALL reuse the tab that shows a page of the same documentation server. In VS Code for the Web, which has no integrated browser, they SHALL open in the Simple Browser as before.

#### Scenario: Two documentation pages on desktop
- **WHEN** the user runs "Open Documentation (deprecated)" on `Collections` and then on `BuiltIn` in desktop VS Code
- **THEN** `BuiltIn` is shown beside the editor, in the tab that showed `Collections`

#### Scenario: VS Code for the Web
- **WHEN** the user runs "Open Documentation (deprecated)" in a Codespace opened in VS Code for the Web
- **THEN** the page opens in the Simple Browser, as before

### Requirement: The heading of the hover links to the Documentation Viewer

In VS Code, the first heading of a hover SHALL be a link to the Documentation Viewer where the hover shows a keyword, a library or a resource file and the documentation actions have a target:
- On a keyword reference in a keyword call, setup, teardown or template, and on the name in a keyword definition header, the link SHALL do what "Show in Documentation Viewer" does at that position: show the page at that keyword.

#### Scenario: Keyword call
- **WHEN** the user hovers over a call of `Remove From List` and clicks the heading `Keyword Remove From List`
- **THEN** a viewer shows `Collections` at `Remove From List`

#### Scenario: Keyword definition
- **WHEN** the user hovers over the name in a keyword definition header of a `.resource` file and clicks the heading
- **THEN** a viewer shows that resource file at the keyword

#### Scenario: Library import
- **WHEN** the user hovers over `Collections` in `Library    Collections` and clicks the heading `Library Collections`
- **THEN** a viewer shows `Collections`

#### Scenario: Resource import
- **WHEN** the user hovers over `sub/local.resource` in `Resource    sub/local.resource` and clicks the heading
- **THEN** a viewer shows `local.resource`

#### Scenario: Library with import arguments
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello`, and the user hovers over `alibrary` in that import
- **THEN** the hover starts with the heading and the arguments of the library's import, that heading is the link, and it shows `alibrary` with the target field `alibrary::a_param=from hello`

#### Scenario: Alias of an import
- **WHEN** the user hovers over `OS` in `Library    OperatingSystem    AS    OS` and clicks the heading `Library OperatingSystem`
- **THEN** a viewer shows `OperatingSystem` from its beginning

#### Scenario: Prefix of a keyword call
- **WHEN** the user hovers over `Collections` in `Collections.Append To List` and clicks the heading `Library Collections`
- **THEN** a viewer shows `Collections` from its beginning, not at `Append To List`

#### Scenario: Pinned viewer
- **WHEN** a viewer that shows `XML` is pinned, and the user clicks the heading of the hover on a call of `Log`
- **THEN** the pinned viewer shows `BuiltIn` at `Log`

#### Scenario: Variables import
- **WHEN** the user hovers over the name of a Variables import
- **THEN** the heading of the hover is no link

#### Scenario: Call of several keywords
- **WHEN** two imported resource files both define `Dup Keyword`, and the user hovers over a call of `Dup Keyword`
- **THEN** the hover shows both keywords, and neither heading is a link

#### Scenario: Other language clients
- **WHEN** a language client other than the VS Code extension, such as the IntelliJ plugin, requests the hover on a call of `Log`
- **THEN** the hover is the same as before this change

### Requirement: Links in documentation open the Documentation Viewer

In VS Code, documentation that RobotCode shows in a hover, in the details of a completion item, in signature help and in a tooltip of the Keywords view SHALL link into the Documentation Viewer. Its target is the library, resource file or suite file it documents:
- in a hover, the target of the requirement "The heading of the hover links to the Documentation Viewer";
- in a tooltip of the Keywords view, the import of the item, or the current file for its own keywords.

#### Scenario: Keyword named in Markdown documentation
- **WHEN** the user hovers over a call of `Log` on RF 7.5 and clicks `Set Log Level` in its documentation
- **THEN** a viewer shows `BuiltIn` at `Set Log Level`

#### Scenario: Keyword named in Robot Framework's format
- **WHEN** the user hovers over a call of `Run Keyword If` on RF 7.4 and clicks `Run Keyword` in its documentation
- **THEN** a viewer shows `BuiltIn` at `Run Keyword`

#### Scenario: Section named in a keyword's documentation
- **WHEN** the user hovers over a call of `Log` on RF 7.5 and clicks `String representations`
- **THEN** a viewer shows `BuiltIn` at the section `String representations`

#### Scenario: Type in the argument table
- **WHEN** the user hovers over a call of `Convert To Integer` on RF 7.5 and clicks the type `int` of the argument `base`
- **THEN** a viewer shows `BuiltIn` at the data type `integer`

#### Scenario: Return type
- **WHEN** the user hovers over a call of `Parse Xml` on RF 7.5 and clicks the return type `Element`
- **THEN** a viewer shows `XML` at the data type `Element`

#### Scenario: Type whose heading has a numbered anchor
- **WHEN** a library documented in Markdown has the keyword `Color Enum`, the `Enum` `Color` and the keyword `Paint` with the argument `shade: Color`, and the user clicks `Color` in the hover of `Paint`
- **THEN** a viewer shows the library at the heading `Color (Enum)`, not at the keyword `Color Enum`

#### Scenario: Table of contents
- **WHEN** the user hovers over `BuiltIn` in `Library    BuiltIn` and clicks the entry `Evaluating expressions` of the table of contents
- **THEN** a viewer shows `BuiltIn` at the section `Evaluating expressions`, and no other editor opens

#### Scenario: Link of the author in HTML
- **WHEN** a library documented in HTML has the link `<a href="#usage">usage</a>` in a keyword's documentation, its introduction has the heading `Usage`, and the user clicks the link in the hover of that keyword
- **THEN** a viewer shows the library at `Usage`

#### Scenario: Name without a heading on the page
- **WHEN** the documentation of a keyword names a private keyword of its library
- **THEN** the name stays inline code in the hover

#### Scenario: Keyword added since the page was generated
- **WHEN** a resource file was shown in this session, the user then adds the keyword `New Keyword`, names it in the documentation of the keyword `Old Keyword` of the same file and saves, and clicks `New Keyword` in the hover of a call of `Old Keyword`
- **THEN** the viewer shows the resource file at `New Keyword`

#### Scenario: Hover without a target
- **WHEN** two imported resource files both define `Dup Keyword`, whose documentation has the link `[usage](#usage)`, and the user hovers over a call of `Dup Keyword`
- **THEN** `usage` is text, and clicking it opens nothing

#### Scenario: Completion of a keyword
- **WHEN** the user completes a keyword call on RF 7.5, selects `Log` in the list, and clicks `Set Log Level` in its details
- **THEN** a viewer shows `BuiltIn` at `Set Log Level`
- **AND** the heading `Keyword Log` of the details shows `BuiltIn` at `Log`

#### Scenario: Completion of a library name
- **WHEN** the user completes the name in `Library    ` on RF 7.5, selects `XML`, and clicks an entry of the table of contents in its details
- **THEN** a viewer shows `XML` at that section

#### Scenario: Signature help
- **WHEN** the user types the arguments of `Run Keyword If` on RF 7.4 and clicks `Run Keyword` in the documentation of the signature help
- **THEN** a viewer shows `BuiltIn` at `Run Keyword`

#### Scenario: Tooltip of the Keywords view
- **WHEN** the user clicks `Set Log Level` in the tooltip of `Log` under `BuiltIn` in the Keywords view on RF 7.5
- **THEN** a viewer shows `BuiltIn` at `Set Log Level`

#### Scenario: Documentation too long for links
- **WHEN** the documentation of a library with links would be longer than 100,000 characters
- **THEN** its heading is a link, and its references are inline code and its links to `#…` text

#### Scenario: Hover links in other language clients
- **WHEN** a language client other than the VS Code extension requests the hover of a call of `Log` on RF 7.5, or the details of `Log` in a completion list
- **THEN** `Set Log Level` is inline code, and the documentation is the same as before this change

### Requirement: Documentation runs only the viewer's command

In VS Code, a `command:` link in documentation that RobotCode shows, in a hover, in the documentation of a completion item, in signature help or in a tooltip of the Keywords view, SHALL run only when it shows documentation in the Documentation Viewer. Every other `command:` link, such as one written in a library's documentation, SHALL do nothing when it is clicked.

#### Scenario: Command link of a library's author
- **WHEN** the documentation of a keyword contains the link `[quit](command:workbench.action.quit)`, and the user clicks it in the hover of a call of that keyword
- **THEN** nothing happens, and VS Code keeps running

#### Scenario: Command link in a tooltip of the Keywords view
- **WHEN** the user clicks the same link in the tooltip of that keyword in the Keywords view
- **THEN** nothing happens

#### Scenario: Viewer links still run
- **WHEN** the user clicks the heading of the hover on a call of that keyword
- **THEN** a viewer shows its library at the keyword

### Requirement: A page opens as Markdown

The toolbar of a viewer SHALL have the button "Open as Markdown", after the refresh button. Choosing it SHALL open the Markdown of the page the viewer shows, as `robotcode doc lib` produced it, as a new untitled Markdown document in the viewer's editor group, with the focus. Saving the document SHALL ask for a file name. The viewer SHALL keep its target, position and history.

#### Scenario: BuiltIn as Markdown
- **WHEN** a viewer shows `BuiltIn` and the user chooses "Open as Markdown"
- **THEN** an untitled Markdown document opens in the viewer's editor group and has the focus, and its text is the Markdown of the page, starting with `# Library *BuiltIn*`
- **AND** when the user switches back to the viewer, it shows `BuiltIn` at the same position, and back works as before

#### Scenario: Save the Markdown
- **WHEN** the user saves that document
- **THEN** VS Code asks for a file name

#### Scenario: Viewer in a window of its own
- **WHEN** a viewer that was moved into a window of its own shows `Collections`, and the user chooses "Open as Markdown"
- **THEN** the document opens in that window, in the viewer's editor group

#### Scenario: Error above a kept page
- **WHEN** a viewer shows the error of a failed generation above the kept page of `ArgLib`, and the user chooses "Open as Markdown"
- **THEN** the document holds the kept page

#### Scenario: No page
- **WHEN** a viewer shows the error of a target without a kept page
- **THEN** "Open as Markdown" is disabled, and pressing Enter on it opens nothing

### Requirement: What the documentation actions show

"Show in Documentation Viewer" SHALL show the documentation of that library, resource file or suite file in the viewer chosen by the requirement "Which viewer shows documentation from the editor". "Show in New Documentation Viewer" SHALL show it in a new viewer. For a keyword position, both SHALL show the page at that keyword. "Open Documentation (deprecated)" SHALL open the Libdoc page, at the keyword for a keyword position.

#### Scenario: New viewer at a keyword
- **WHEN** the user chooses "Show in New Documentation Viewer" on a call of `Remove From List`
- **THEN** a new viewer shows `Collections` at `Remove From List`

### Requirement: Preferred source action

"Show in Documentation Viewer" SHALL be the preferred source action; the other two SHALL NOT. RobotCode SHALL NOT define a key binding for the source actions.

#### Scenario: Preferred action on a keyword call
- **WHEN** source actions are requested on a call of `Log`
- **THEN** "Show in Documentation Viewer" is the only preferred source action among the three

### Requirement: A key of the user runs the preferred source action

A key that the user binds to VS Code's command `editor.action.sourceAction` with the arguments `{"kind": "source", "preferred": true, "apply": "first"}` SHALL run "Show in Documentation Viewer" at the cursor, without a menu; where the cursor offers no documentation, it SHALL open nothing, and VS Code SHALL report that no preferred source action is available.

#### Scenario: Own key on a library import
- **WHEN** the user has bound a key to `editor.action.sourceAction` with the arguments `{"kind": "source", "preferred": true, "apply": "first"}`, the cursor is on `Collections` in `Library    Collections`, and the user presses that key
- **THEN** a viewer shows `Collections`, and no menu is shown

### Requirement: Relative paths in the documented import

A relative path in the import that the documentation actions document SHALL be resolved against the directory of the file that contains the import, also when that file is a resource file imported by the current document, and `${CURDIR}` SHALL be that directory.

#### Scenario: CURDIR in a resource import of a resource file
- **WHEN** a suite imports `sub/local.resource`, which imports `${CURDIR}/deeper/nested.resource`, and the user chooses "Show in Documentation Viewer" on a call of a keyword of `nested.resource` in the suite
- **THEN** the viewer shows `nested.resource`

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

### Requirement: Context menu of the Keywords view

The context menu of each import and keyword item of the Keywords view SHALL offer, in this order: "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Show Documentation (deprecated)". "Show Documentation (deprecated)" SHALL open the Libdoc page, as the requirement "Libdoc pages open beside the editor" describes.

#### Scenario: New viewer from the context menu
- **WHEN** the user chooses "Show in New Documentation Viewer" in the context menu of the keyword `Remove From List` under `Collections` in the Keywords view
- **THEN** a new viewer shows `Collections` at `Remove From List`

### Requirement: A viewer keeps its state

A viewer SHALL keep its target, position, history, filter, whether its outline is shown, and the state of its pin button when its tab is hidden and shown again, when it is moved, and after a reload of the window. Splitting or copying a viewer and reopening a closed viewer are not required.

#### Scenario: Moved into another editor group
- **WHEN** a viewer shows `XML` with the filter `list` and is moved into another editor group
- **THEN** it shows `XML` at the same position with the filter `list`

#### Scenario: Hidden outline after a reload
- **WHEN** the window is reloaded while a viewer that shows `XML` has its outline hidden
- **THEN** the viewer shows `XML` with its outline hidden

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

### Requirement: Switching the workspace folder of a viewer

Entering an absolute path in the target field that lies in another workspace folder SHALL switch the viewer to that folder. In a workspace with more than one folder, the toolbar of a viewer SHALL show the name of the viewer's folder before the pin button. Choosing it SHALL let the user pick another workspace folder; the viewer SHALL then show its current target for the picked folder, as a new history entry. In a workspace with one folder, the toolbar SHALL show no folder.

#### Scenario: Picked folder as a history entry
- **WHEN** a viewer of the folder `tests` shows `Collections`, and the user picks the folder `shared` in its toolbar
- **THEN** the viewer shows `Collections` for `shared` as a new history entry, and back shows `Collections` of `tests`

### Requirement: Targets that start with a dash

A target that starts with `-`, such as the file `-shared.resource`, SHALL be shown like any other target.

#### Scenario: Dash target and back
- **WHEN** the workspace folder contains the resource file `-shared.resource`, and the user enters `-shared.resource` in a viewer that shows `BuiltIn`
- **THEN** the viewer shows the keywords of that file, and back returns to `BuiltIn`

### Requirement: Tooltips of the viewer's buttons

The buttons of the toolbar and of the find bar of a viewer SHALL show their names as tooltips.

#### Scenario: Tooltip of the refresh button
- **WHEN** the user rests the mouse on the refresh button of a viewer
- **THEN** the tooltip shows the name of the button

### Requirement: Targets whose documentation cannot be generated

When the documentation of an entered target cannot be generated, the viewer SHALL show the error. If no page of that target was kept before, it SHALL also show a way to retry. The field SHALL keep the entered text, and back SHALL return to the previous page. A Python environment that cannot run Robot Framework, and a folder for which RobotCode is switched off, SHALL NOT count as such an error (requirement "A viewer says that it waits").

#### Scenario: Import arguments that fail
- **WHEN** a library `StrictLib` raises for the unknown mode `bogus`, no page of `StrictLib::bogus` was kept before, and the user enters `StrictLib::bogus`
- **THEN** the viewer shows the error and a way to retry, and the field keeps `StrictLib::bogus`

### Requirement: Back and forward in a viewer

Back and forward SHALL be offered:
- as toolbar buttons;
- as the keys Alt+Left and Alt+Right, or Cmd+[ and Cmd+] on macOS, while the viewer has the focus;
- as the mouse's back and forward buttons.

While the viewer has the focus, these keys SHALL act only on the viewer.

#### Scenario: Back button of the toolbar
- **WHEN** the user follows a link in a viewer and then clicks the back button of its toolbar
- **THEN** the viewer shows the entry before the link

### Requirement: Find in the page

Ctrl+F, or Cmd+F on macOS, SHALL open a find bar that searches only the page, also while a keyboard layout without Latin letters is active. It SHALL show the number of matches and which one is current, and mark the matches, also in high contrast themes. Enter SHALL go to the next match and Shift+Enter to the previous one.

#### Scenario: Previous match
- **WHEN** the find bar of a viewer shows several matches and the user presses Shift+Enter
- **THEN** the previous match becomes the current one

### Requirement: What the find bar matches

The find bar SHALL match the text as the page displays it: whitespace in the search text SHALL match any whitespace within a paragraph, heading, list item or table cell, such as a line break of the documentation source. While the find bar is open, a page that the viewer shows SHALL open where it would open without the find bar; the bar searches it again, and the first match in view becomes the current one.

#### Scenario: Another target while the find bar is open
- **WHEN** the find bar of a viewer that shows `BuiltIn` is open with `list`, and the user enters `Collections` in the target field
- **THEN** the viewer shows `Collections` from its start, and the bar searches `Collections` for `list`

### Requirement: Showing in a new viewer

"Show in New Documentation Viewer" and the second item action of the Keywords view SHALL always open a new viewer, also when a viewer is pinned; the new viewer is then the viewer used last.

#### Scenario: New viewer becomes the one used last
- **WHEN** no viewer is pinned, a viewer shows `XML`, the user chooses "Show in New Documentation Viewer" on `Library    Collections`, and then "Show in Documentation Viewer" on a call of `Log`
- **THEN** the new viewer shows `BuiltIn` at `Log`, and the first viewer still shows `XML`

### Requirement: One pinned viewer

At most one viewer SHALL be pinned; pinning one SHALL unpin the others. After a reload of the window, a restored viewer SHALL count for the choice of the viewer only once its tab has been shown.

#### Scenario: Pinning a second viewer
- **WHEN** one viewer is pinned and the user pins another viewer
- **THEN** the first viewer is no longer pinned

### Requirement: Where a viewer opens

A new viewer SHALL open beside the active editor, where the editor keeps the focus. When the setting `robotcode.documentationViewer.openLocation` is `active`, it SHALL open in the active editor group instead. A viewer in another window SHALL be brought to the front there. Navigation within a viewer SHALL stay in that viewer.

#### Scenario: Link within a viewer that is not pinned
- **WHEN** another viewer is pinned and the user follows a link within a viewer that is not pinned
- **THEN** the viewer that is not pinned shows the target of the link, and the pinned viewer is unchanged

### Requirement: Generated pages are kept

The last generated page of each target SHALL be kept per workspace folder, Python environment, selected profiles and the settings `robotcode.robot.pythonPath`, `robotcode.robot.languages`, `robotcode.robot.variables`, `robotcode.robot.variableFiles` and `robotcode.robot.env`, also across restarts; at least the pages of the 50 most recently generated targets SHALL be kept.

#### Scenario: Page after a restart
- **WHEN** a viewer showed `Collections`, VS Code is restarted, and a viewer shows `Collections` again
- **THEN** the kept page of `Collections` is shown at once

### Requirement: Showing and refreshing a kept page

Showing a target SHALL show its kept page at once, if there is one. It SHALL generate the page again in the background once per session, and update the view when the result differs. The refresh button SHALL generate it again. When a generation fails, the viewer SHALL show the error, above the kept page if there is one.

#### Scenario: Refresh button
- **WHEN** the user chooses the refresh button of a viewer that shows `Collections`
- **THEN** the page of `Collections` is generated again

### Requirement: A missing keyword generates the page again

When documentation is shown at a keyword that the page does not have, for example a keyword added since the page was generated, the viewer SHALL generate the page again, once, and show it at the keyword if the new page has it.

#### Scenario: Keyword the kept page does not have
- **WHEN** documentation is shown at a keyword that the kept page of its target does not have
- **THEN** the viewer generates the page again once, and shows it at the keyword if the new page has it

### Requirement: Hover links on imports, aliases and prefixes

On the name of a Library or Resource import, the link of the hover's heading SHALL do what "Show in Documentation Viewer" does there. On the alias of a Library import, and on the library or resource prefix of a keyword call, where the hover shows the library or resource file, the link SHALL show the page of that import without going to a keyword.

#### Scenario: Alias of Collections
- **WHEN** the user hovers over `Coll` in `Library    Collections    AS    Coll` and clicks the heading
- **THEN** a viewer shows `Collections` from its beginning

### Requirement: Viewer and text of the hover link

The link of the hover's heading SHALL show the documentation in the viewer chosen by the requirement "Which viewer shows documentation from the editor", for the import named by the requirement "Documentation actions document the import the analysis used". The heading SHALL keep its text and stay a heading, and its tooltip SHALL be "Show in Documentation Viewer".

#### Scenario: Library import with a pinned viewer
- **WHEN** a viewer that shows `XML` is pinned, and the user clicks the heading of the hover on `Collections` in `Library    Collections`
- **THEN** the pinned viewer shows `Collections`

### Requirement: Hovers without a link

The hover SHALL have no link where there is no such target: on a Variables import and on a call that matches several keywords. The hover of a variable or a test case SHALL have no link. Language clients other than the VS Code extension, such as the IntelliJ plugin, SHALL get the hover without links.

#### Scenario: Hover of a variable
- **WHEN** the user hovers over a variable
- **THEN** the heading of the hover is no link

### Requirement: Link target in a completion item

In a completion item, the target of the documentation links SHALL be the import the item comes from: for a keyword the import of that keyword, for a library or resource the item itself, and for a library name or resource path in an import, that library or file without import arguments; for a named argument or a value of an argument, the import of the called keyword, or the library of the import whose arguments are completed.

#### Scenario: Heading of a completed library name
- **WHEN** the user completes the name in `Library    ` on RF 7.5, selects `Collections`, and clicks the heading of its details
- **THEN** a viewer shows `Collections`

### Requirement: Link target in signature help

In signature help, the target of the documentation links SHALL be the import of the keyword whose signature is shown, also for the outer keyword of `Run Keyword` and its variants, or the library of the import whose arguments are shown.

#### Scenario: Signature help of Log
- **WHEN** the user types the arguments of `Log` on RF 7.5 and clicks `Set Log Level` in the documentation of the signature help
- **THEN** a viewer shows `BuiltIn` at `Set Log Level`

### Requirement: Heading and type links in documentation with a target

Variables imports and their files have no target. In documentation with a target, the first heading of the documentation of a keyword, a library or a resource file in a completion item and in the tooltip of an import SHALL be a link, as the heading of a hover is. A type in the argument table or in the return type that has a heading in `Data types` of the page SHALL be a link that shows the page at that data type.

#### Scenario: Heading of an import tooltip
- **WHEN** the user opens the tooltip of the import `BuiltIn` in the Keywords view and clicks its heading
- **THEN** a viewer shows `BuiltIn`

### Requirement: Names in documentation link to the page

In documentation with a target, a name that refers to a keyword, a data type or a section of the same library or resource file, in its documentation, in the description of an argument, a return value or an exception, written as a name in single backticks in Robot Framework's format or as a Markdown reference link, SHALL be a link that shows the page at that keyword, data type or section.

#### Scenario: Section named in completion details
- **WHEN** the user selects `Log` in a keyword completion list on RF 7.5 and clicks `String representations` in its details
- **THEN** a viewer shows `BuiltIn` at the section `String representations`

### Requirement: Links to places in the documentation

In documentation with a target, a link to a place in the documentation itself (`#…`), such as an entry of a table of contents or a link of the documentation's author, in Markdown or in HTML, SHALL show the page at that place.

#### Scenario: Link of the author in Markdown
- **WHEN** a library documented in Markdown has the link `[usage](#usage)` in a keyword's documentation, its introduction has the heading `Usage`, and the user clicks the link in the hover of that keyword
- **THEN** a viewer shows the library at `Usage`

### Requirement: How documentation links behave

Each documentation link SHALL show the page in the viewer chosen by the requirement "Which viewer shows documentation from the editor", for the import named by the requirement "Documentation actions document the import the analysis used", and SHALL add a history entry. The links SHALL keep their text, code SHALL stay unchanged, and their tooltip SHALL be "Show in Documentation Viewer".

#### Scenario: Back after a link
- **WHEN** a viewer shows `XML`, the user clicks `Set Log Level` in the hover of a call of `Log` on RF 7.5, and then goes back in that viewer
- **THEN** the viewer shows `XML` again

### Requirement: Names without a heading stay inline code

A name without a heading on the page, such as a private keyword, a name of another library or a default section the page does not have, SHALL stay inline code.

#### Scenario: Keyword of another library
- **WHEN** the documentation of a keyword names a keyword of another library
- **THEN** the name stays inline code in the hover

### Requirement: Documentation too long for links

When the links would make the documentation longer than the 100,000 characters that VS Code shows, it SHALL keep only the link of its heading, with references as inline code and links to `#…` as text.

#### Scenario: Long keyword documentation
- **WHEN** the documentation of a keyword with links would be longer than 100,000 characters
- **THEN** only its heading is a link

### Requirement: Pages without the linked place

When the page does not have the keyword, data type or place of a documentation link, for example one added since the page was generated, the viewer SHALL generate the page again, once, and show it there if the new page has it, and otherwise from its start. Without VS Code's Markdown support, the viewer is not required to scroll there.

#### Scenario: Place the new page does not have either
- **WHEN** a link shows the page at a data type that neither the kept page nor the newly generated page has
- **THEN** the viewer shows the page from its start

### Requirement: Documentation without a target and other clients

In documentation without a target, VS Code SHALL show links to a place in the documentation itself as text. Language clients other than the VS Code extension SHALL get all documentation as before: references as inline code and links to `#…` as they are.

#### Scenario: Completion details in the IntelliJ plugin
- **WHEN** the IntelliJ plugin requests the details of `Log` in a completion list on RF 7.5
- **THEN** `Set Log Level` is inline code

### Requirement: Open as Markdown without a page

While the viewer shows no page, such as while the first page of a target is generated or after a generation failed without a kept page, the button "Open as Markdown" SHALL be disabled, also for the keyboard.

#### Scenario: First page still generated
- **WHEN** the first page of a target is still being generated
- **THEN** "Open as Markdown" is disabled

### Requirement: Outline of a viewer

Next to the page, the viewer SHALL show an outline as a tree while the outline is shown (requirement "Showing and hiding the outline"), like the sidebar of the REPL's documentation viewer: the level-2 headings of the page, below each of them its level-3 headings, and below each section of the introduction its subsections, to any depth. Keywords, data types and the entries of `Importing` SHALL have no entries below them.

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
- **WHEN** `robotcode.documentationViewer.showOutline` is `false` and the user runs "RobotCode: New Documentation Viewer"
- **THEN** the new viewer shows `BuiltIn` with its outline hidden, and the outline button shows the outline when clicked

#### Scenario: Setting changed while a viewer is open
- **WHEN** a viewer shows its outline and the user sets `robotcode.documentationViewer.showOutline` to `false`
- **THEN** that viewer keeps its outline, and the next new viewer starts without it

### Requirement: The page while the environment is not usable

While RobotCode has not found the Python environment of a viewer's folder usable, showing a target SHALL show the page that its history entry showed last, if there is one. While the environment is not usable, the refresh button SHALL first check the environment again.

#### Scenario: Restart before the environment is known
- **WHEN** a viewer showed `Collections`, VS Code is restarted, and the Python side selects the folder's environment only some seconds after the viewer is restored
- **THEN** the viewer shows the page of `Collections` at once and no error, and generates it again in that environment once RobotCode has checked it

#### Scenario: Refresh while the environment has a problem
- **WHEN** a viewer shows the error that the selected Python environment of its folder has no Robot Framework, Robot Framework has just been installed into that environment, and the user chooses the refresh button
- **THEN** RobotCode checks the environment again, and the viewer shows the page

### Requirement: Generation waits for a usable Python environment

A viewer SHALL generate a page only when RobotCode's check finds the Python environment of its workspace folder usable, the check that the language server waits for too, and SHALL generate with the interpreter of that check. When the environment becomes usable, a viewer that waits for it SHALL load its page by itself.

#### Scenario: Robot Framework installed later
- **WHEN** a viewer waits because the selected Python environment of its folder has no Robot Framework, and the user installs Robot Framework into that environment in a terminal
- **THEN** within a few seconds the viewer shows its page, without any action in the viewer

#### Scenario: Interpreter selected later
- **WHEN** a viewer waits because no Python interpreter is selected for its folder, and the user selects an environment with Robot Framework
- **THEN** the viewer shows its page, generated with that environment

### Requirement: A viewer says that it waits

While the Python environment of a viewer's folder cannot run Robot Framework, the viewer SHALL say above the page it shows, if there is one, that it waits for that environment, with its progress bar running. When the problem has lasted 30 seconds, the viewer SHALL show it as an error that names the problem, without a way to retry. When RobotCode is switched off for the folder, the viewer SHALL show that as an error at once.

#### Scenario: Problem that solves itself at startup
- **WHEN** at startup RobotCode's first check finds the global interpreter without Robot Framework, and the Python side selects the folder's `.venv` with Robot Framework some seconds later
- **THEN** the viewer shows its progress bar and that it waits for the Python environment, and no error, and then its page, generated with `.venv`

#### Scenario: Problem that lasts
- **WHEN** a viewer waits for the environment of its folder, and that environment still has no Robot Framework 30 seconds after RobotCode found that
- **THEN** the viewer shows the error that the selected Python environment has no Robot Framework, with no way to retry
- **AND** it shows its page by itself once Robot Framework is installed into that environment

#### Scenario: Environment without Robot Framework
- **WHEN** the selected Python environment of the folder has had no Robot Framework for more than 30 seconds, and the user enters `Collections` in a viewer
- **THEN** the viewer shows the error that this environment has no Robot Framework at once, with no way to retry, and no generation runs

#### Scenario: Switched-off folder
- **WHEN** `robotcode.disableExtension` is `true` in the folder of a viewer, and the viewer shows `Collections`
- **THEN** the viewer shows the error that RobotCode is switched off for the folder, and shows the page once the setting is removed

### Requirement: A viewer follows the environment of its folder

When the Python environment of a viewer's workspace folder becomes usable with another interpreter than the one its page was generated with, the viewer SHALL load the page again, as it does when the page is shown: the kept page for that interpreter at once, if there is one, then a generation once per session.

#### Scenario: Another environment selected
- **WHEN** a viewer shows `Collections` generated with the folder's `.venv`, and the user selects another environment with Robot Framework for the folder
- **THEN** the viewer shows `Collections` generated with that environment, without any action in the viewer

#### Scenario: Wrong interpreter at startup
- **WHEN** at startup RobotCode's first check finds the global interpreter usable, a viewer shows `Collections` generated with it, and the Python side then selects the folder's `.venv`
- **THEN** the viewer shows `Collections` generated with `.venv`

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

### Requirement: Completion of the target's name

The list SHALL complete the text before the first `::` as RobotCode completes `Library` and `Resource` imports in the editor: modules on the Python path, the standard libraries with `BuiltIn`, and library, resource and suite files and directories, relative to the viewer's workspace folder or absolute. It SHALL offer one level at a time, the names that start with the typed part of that level, without regard to case. A text with `::`, or of dots only, SHALL get no completion.

#### Scenario: Standard library

- **WHEN** the user types `Coll`
- **THEN** the list offers `Collections`

#### Scenario: BuiltIn

- **WHEN** the user types `Bui`
- **THEN** the list offers `BuiltIn`, which the editor's completion of `Library` imports leaves out because every file imports it already

#### Scenario: Dots only

- **WHEN** the user types `..`
- **THEN** no list opens

#### Scenario: Directory and file of the folder

- **WHEN** the workspace folder contains `resources/shop.resource`, and the user types `res`
- **THEN** the list offers the directory `resources`
- **AND** after the user types `resources/`, the list offers `shop.resource`

#### Scenario: Module on the Python path

- **WHEN** the setting `robotcode.robot.pythonPath` holds `libraries`, the directory `libraries` contains `ShopLibrary.py`, and the user types `Shop`
- **THEN** the list offers `ShopLibrary`

#### Scenario: Import arguments

- **WHEN** the list offers `Collections`, and the user types `Collections::`
- **THEN** the list closes

### Requirement: Order of the suggestions

The list SHALL order its completions as the editor's completion does: first the names that continue the typed part in the same case, then the others, each alphabetically without regard to case. Of two equal names, a module SHALL come before a file, and a file before a directory. The bookmarks SHALL come before the completions.

#### Scenario: Typed with a capital letter

- **WHEN** no bookmark contains `Coll`, and the user types `Coll`
- **THEN** the list offers `Collections` first, then `collections` as a module, then `collections` as a directory

#### Scenario: Typed in small letters

- **WHEN** no bookmark contains `xml`, and the user types `xml`
- **THEN** the list offers `xml` as a module first, then `xml` as a directory, and `XML` only after the names that start with `xml`

### Requirement: Choosing a suggestion

When the list opens, its first suggestion SHALL be selected, and Up and Down SHALL select another. Enter SHALL put the selected suggestion into the target field and load it, and a click on a suggestion SHALL do the same. Tab SHALL put it into the field without loading it. Enter and Tab SHALL put a selected directory into the field with a `/` at its end, and the list SHALL then offer its content. With the list closed, Enter SHALL load the text of the field, as before.

#### Scenario: Enter on a file

- **WHEN** the list offers `shop.resource` for `resources/`, and the user selects it and presses Enter
- **THEN** the viewer shows `resources/shop.resource`

#### Scenario: Enter on a directory

- **WHEN** the list offers the directory `resources`, and the user selects it and presses Enter
- **THEN** the field holds `resources/`, the list offers `shop.resource`, and the viewer still shows the page it showed before

#### Scenario: Enter on the first suggestion

- **WHEN** the user types `Coll` and presses Enter as soon as the list offers `Collections`
- **THEN** the viewer shows `Collections`

#### Scenario: Typing on while the list is open

- **WHEN** the list offers `XML` for `XM`, and the user types `L::use_lxml=False` and presses Enter at once
- **THEN** the viewer loads `XML::use_lxml=False` as typed

#### Scenario: Tab

- **WHEN** a viewer shows `BuiltIn`, and the user types `Coll` and presses Tab as soon as the list offers `Collections`
- **THEN** the field holds `Collections`, the list is closed, and the viewer still shows `BuiltIn`

#### Scenario: Click

- **WHEN** the list offers `Collections` and the user clicks it
- **THEN** the viewer shows `Collections`

#### Scenario: Enter with the list closed

- **WHEN** the user types `Coll`, closes the list with Escape and presses Enter
- **THEN** the viewer loads `Coll` as typed and shows the error that its documentation cannot be generated

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
