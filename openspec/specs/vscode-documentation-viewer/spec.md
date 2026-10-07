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
- **THEN** the viewer's target field shows `alibrary` without arguments, and the viewer shows its page instead of the error of `alibrary::port=80x`

#### Scenario: Resource imported through a resource in another directory
- **WHEN** a suite imports `sub/local.resource`, which imports `deeper/nested.resource`, and documentation is opened on a call of a keyword of `nested.resource` in the suite
- **THEN** "Open Documentation (deprecated)" and the Documentation Viewer both show `nested.resource`
- **AND** the viewer's target field shows the path of `nested.resource` relative to the workspace folder

#### Scenario: Second import of the same library
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello` and with `a_param=${LIB_ARG}` as `lib_var`, `${LIB_ARG}` is `from lib`, and documentation is opened on `lib_var.A Library Keyword`
- **THEN** the viewer's target field shows `alibrary::a_param=from lib`, and the URL of "Open Documentation (deprecated)" carries `a_param=from lib`
- **AND** on `lib_hello.A Library Keyword` they carry `a_param=from hello`, also when the analysis of the suite was restored from the cache

#### Scenario: Call without a prefix decided by the search order
- **WHEN** a suite imports `alibrary` as `lib_hello` and as `lib_var` as above, `robotcode.analysis.robot.globalLibrarySearchOrder` is `["lib_var"]`, and documentation is opened on a call of `A Library Keyword` without a prefix
- **THEN** the viewer's target field shows `alibrary::a_param=from lib`, and the URL of "Open Documentation (deprecated)" carries `a_param=from lib`, also when the analysis of the suite was restored from the cache

#### Scenario: Module library from two directories
- **WHEN** the user chooses "Show in Documentation Viewer" on `Library    Collections` in two suites in different directories
- **THEN** the viewer's target field shows `Collections` both times

#### Scenario: Hover link on the second import
- **WHEN** the suite above is open and the user clicks the heading of the hover on `lib_var.A Library Keyword`
- **THEN** the viewer's target field shows `alibrary::a_param=from lib`, also when the analysis of the suite was restored from the cache

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
- **WHEN** the user runs "RobotCode: Open Documentation Viewer" while a file of a workspace folder is the active editor
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
- **WHEN** the user runs "Open Documentation Viewer in New Window" while a viewer that shows `BuiltIn` is active
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

The toolbar of a viewer SHALL have a target field. It SHALL show what the viewer documents, as `Name`, `Name::arg1::arg2` or the path of a library, resource or suite file, relative to the viewer's workspace folder or absolute. Entering another target SHALL show its documentation in the same tab, which takes the new name as its title. Entering the target that is already shown SHALL refresh it.

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

A viewer SHALL keep a history of what it showed. Choosing an outline entry, following a link within the page, entering a target, picking another workspace folder, and documentation shown by an action from the editor or the Keywords view SHALL each add an entry. Entering the target that is already shown SHALL only refresh it. Choosing the outline entry, or following a link, to the heading the current entry shows SHALL only show that heading again.

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
- **THEN** the viewer's target field shows `alibrary::a_param=from hello`

### Requirement: Documented import of a call without a prefix

For a keyword call without a prefix, the documentation actions SHALL document the import the analysis resolved the call to, also when the same library is imported twice with different arguments and the library search order or the keywords of the two imports decide.

#### Scenario: Search order naming the first import
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello` and with `a_param=from lib` as `lib_var`, `robotcode.analysis.robot.globalLibrarySearchOrder` is `["lib_hello"]`, and documentation is opened on a call of `A Library Keyword` without a prefix
- **THEN** the viewer's target field shows `alibrary::a_param=from hello`

### Requirement: Documented library loaded without the import's arguments

A library that the analysis loaded without the import's arguments, because loading it with them failed, SHALL be shown by the documentation actions without arguments, as hover, completion and signature help show it.

#### Scenario: Keyword of a library whose arguments fail
- **WHEN** a suite imports `alibrary` with `port=80x`, which the analysis loads without arguments, and the user chooses "Show in Documentation Viewer" on a call of `A Library Keyword`
- **THEN** the viewer's target field shows `alibrary` without arguments

### Requirement: Context menu of the Keywords view

The context menu of each import and keyword item of the Keywords view SHALL offer, in this order: "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Show Documentation (deprecated)". "Show Documentation (deprecated)" SHALL open the Libdoc page, as the requirement "Libdoc pages open beside the editor" describes.

#### Scenario: New viewer from the context menu
- **WHEN** the user chooses "Show in New Documentation Viewer" in the context menu of the keyword `Remove From List` under `Collections` in the Keywords view
- **THEN** a new viewer shows `Collections` at `Remove From List`

### Requirement: A viewer keeps its state

A viewer SHALL keep its target, position, history, filter and the state of its pin button when its tab is hidden and shown again, when it is moved, and after a reload of the window. Splitting or copying a viewer and reopening a closed viewer are not required.

#### Scenario: Moved into another editor group
- **WHEN** a viewer shows `XML` with the filter `list` and is moved into another editor group
- **THEN** it shows `XML` at the same position with the filter `list`

### Requirement: The command Open Documentation Viewer

The command "RobotCode: Open Documentation Viewer" SHALL open a new viewer on `BuiltIn` of the workspace folder, with the target field focused and its text selected. The workspace folder is the one of the active editor. Without an active editor in a folder, the only folder is used; with several folders, the user SHALL choose one. Without a workspace folder, the commands SHALL show an error message.

#### Scenario: Several folders without an active editor
- **WHEN** a workspace has two folders, no editor is active, and the user runs "RobotCode: Open Documentation Viewer"
- **THEN** the user is asked to choose one of the two folders

### Requirement: The command Open Documentation Viewer in New Window

The command "RobotCode: Open Documentation Viewer in New Window" SHALL open a new viewer in a new window. It SHALL show the target of the active viewer, or else of the viewer used last; without any viewer it SHALL show `BuiltIn`.

Both commands SHALL be in the command palette. The second command SHALL also be in the context menu of the active viewer's tab.

#### Scenario: New window without a viewer
- **WHEN** no viewer is open and the user runs "RobotCode: Open Documentation Viewer in New Window"
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

When the documentation of an entered target cannot be generated, the viewer SHALL show the error. If no page of that target was kept before, it SHALL also show a way to retry. The field SHALL keep the entered text, and back SHALL return to the previous page.

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
