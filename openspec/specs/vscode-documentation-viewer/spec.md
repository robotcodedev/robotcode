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

Wherever RobotCode offers "Open Documentation", it SHALL also offer the source actions "Show in Documentation Viewer" and "Show in New Documentation Viewer", under the same conditions:
- on the name of a Library or Resource import;
- on a keyword reference in a keyword call, setup, teardown or template;
- on the name in a keyword definition header.

The offered actions and what they document SHALL be the same whether the semantic-model analysis path is enabled or not.

"Show in Documentation Viewer" SHALL show the documentation of that library, resource file or suite file in the viewer chosen by the requirement "Which viewer shows documentation from the editor". "Show in New Documentation Viewer" SHALL show it in a new viewer. For a keyword position, both SHALL show the page at that keyword.

#### Scenario: Library import name
- **WHEN** source actions are requested with the cursor on `Collections` in `Library    Collections`
- **THEN** "Open Documentation", "Show in Documentation Viewer" and "Show in New Documentation Viewer" are offered, all for the library `Collections`

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
- **THEN** the offered actions and what they document are identical

### Requirement: Documentation actions document the import the analysis used

The documentation actions of the editor and the Keywords view SHALL document the import through which the analysis resolved the name at the cursor:
- Variables in the import name and arguments SHALL be replaced with the values the analysis knows; the arguments SHALL be passed as strings.
- A relative path in the import SHALL be resolved against the directory of the file that contains the import, also when that file is a resource file imported by the current document, and `${CURDIR}` SHALL be that directory.
- For a keyword call with a library or resource prefix (`lib_var.A Library Keyword`), the import SHALL be the one the prefix names. When the same library is imported twice with different arguments, a call through the second import's alias SHALL use the second import's arguments.
- For a keyword call without a prefix, the import SHALL be the one the analysis resolved the call to, also when the same library is imported twice with different arguments and the library search order or the keywords of the two imports decide.
- A library imported by module name, such as `BuiltIn` or `Collections`, SHALL be shown with the same target wherever it was shown from.

#### Scenario: Resource imported through a resource in another directory
- **WHEN** a suite imports `sub/local.resource`, which imports `deeper/nested.resource`, and documentation is opened on a call of a keyword of `nested.resource` in the suite
- **THEN** "Open Documentation" and the Documentation Viewer both show `nested.resource`
- **AND** the viewer's target field shows the path of `nested.resource` relative to the workspace folder

#### Scenario: Second import of the same library
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello` and with `a_param=${LIB_ARG}` as `lib_var`, `${LIB_ARG}` is `from lib`, and documentation is opened on `lib_var.A Library Keyword`
- **THEN** the viewer's target field shows `alibrary::a_param=from lib`, and the URL of "Open Documentation" carries `a_param=from lib`
- **AND** on `lib_hello.A Library Keyword` they carry `a_param=from hello`, also when the analysis of the suite was restored from the cache

#### Scenario: Call without a prefix decided by the search order
- **WHEN** a suite imports `alibrary` as `lib_hello` and as `lib_var` as above, `robotcode.analysis.robot.globalLibrarySearchOrder` is `["lib_var"]`, and documentation is opened on a call of `A Library Keyword` without a prefix
- **THEN** the viewer's target field shows `alibrary::a_param=from lib`, and the URL of "Open Documentation" carries `a_param=from lib`, also when the analysis of the suite was restored from the cache

#### Scenario: Module library from two directories
- **WHEN** the user chooses "Show in Documentation Viewer" on `Library    Collections` in two suites in different directories
- **THEN** the viewer's target field shows `Collections` both times

### Requirement: The Keywords view opens documentation at the keyword

Each import and keyword item of the Keywords view SHALL offer "Show in Documentation Viewer" and "Show in New Documentation Viewer", for the same import as the documentation actions of the editor. "Show Documentation" and both viewer actions on a keyword defined in the current document SHALL open the documentation at that keyword.

#### Scenario: Local keyword with "Show Documentation"
- **WHEN** the user chooses "Show Documentation" on a keyword of the current file in the Keywords view
- **THEN** the Libdoc page opens at that keyword

#### Scenario: Local keyword with "Show in Documentation Viewer"
- **WHEN** the user chooses "Show in Documentation Viewer" on a keyword of the current file in the Keywords view
- **THEN** a viewer shows the current file at that keyword

#### Scenario: Library import item
- **WHEN** the user chooses "Show in Documentation Viewer" on the import item `lib_hello` of `alibrary`
- **THEN** a viewer shows `alibrary`, and its target field shows `alibrary::a_param=from hello`

### Requirement: Documentation viewers are editor tabs

A Documentation Viewer SHALL be an editor tab that shows the documentation of one library, resource file or suite file, titled with its name. Several viewers SHALL be possible at the same time. Like an editor, a viewer SHALL be movable into other editor groups and into a window of its own, and SHALL be pinnable. A viewer SHALL keep its target, position, history, filter and the state of its pin button when its tab is hidden and shown again, when it is moved, and after a reload of the window. Splitting or copying a viewer and reopening a closed viewer are not required.

The command "RobotCode: Open Documentation Viewer" SHALL open a new viewer on `BuiltIn` of the workspace folder, with the target field focused and its text selected. The workspace folder is the one of the active editor. Without an active editor in a folder, the only folder is used; with several folders, the user SHALL choose one. Without a workspace folder, the commands SHALL show an error message.

The command "RobotCode: Open Documentation Viewer in New Window" SHALL open a new viewer in a new window. It SHALL show the target of the active viewer, or else of the viewer used last; without any viewer it SHALL show `BuiltIn`.

Both commands SHALL be in the command palette. The second command SHALL also be in the context menu of the active viewer's tab.

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
- Entering an absolute path in the target field that lies in another workspace folder SHALL switch the viewer to that folder.
- In a workspace with more than one folder, the toolbar SHALL show the name of the viewer's folder before the pin button. Choosing it SHALL let the user pick another workspace folder; the viewer SHALL then show its current target for the picked folder, as a new history entry. In a workspace with one folder, the toolbar SHALL show no folder.

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

The toolbar of a viewer SHALL have a target field. It SHALL show what the viewer documents, as `Name`, `Name::arg1::arg2` or the path of a library, resource or suite file, relative to the viewer's workspace folder or absolute. Entering another target SHALL show its documentation in the same tab, which takes the new name as its title. Entering the target that is already shown SHALL refresh it. A target that starts with `-`, such as the file `-shared.resource`, SHALL be shown like any other target.

The buttons of the toolbar and of the find bar SHALL show their names as tooltips.

When the documentation of an entered target cannot be generated, the viewer SHALL show the error. If no page of that target was kept before, it SHALL also show a way to retry. The field SHALL keep the entered text, and back SHALL return to the previous page.

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

Next to the page, the viewer SHALL show an outline: its sections, keywords and data types, as the level-2 and level-3 headings, like the sidebar of the REPL's documentation viewer.
- **Filter field.** It SHALL keep the entries whose titles match the filter text by the pattern rules of `robotcode doc keywords`: contains, `*`, `?` and `[…]`/`[!…]`, ignoring case, spaces and underscores. An invalid pattern SHALL match nothing. A section SHALL stay while it or one of its entries matches.
- **Choosing an entry** SHALL show the page at its heading.
- **Selection.** The entry of the heading the page was shown at SHALL be selected, also in high contrast themes. When the page is shown at another heading, by a link, an action, back or forward, the outline SHALL scroll that entry into view.
- **Keyboard.**
  - Up and Down SHALL move the focus to the previous and next visible entry.
  - Right SHALL expand a collapsed section or move to its first entry. Left SHALL collapse an expanded section or move to the entry's section.
  - Home and End SHALL move to the first and last visible entry. Page Up and Page Down SHALL move by one visible page of entries.
  - Enter SHALL choose the focused entry.
  - Typing SHALL move the focus to the next visible entry whose title starts with the typed text.
  - The outline SHALL NOT consume key combinations with Alt, Ctrl or Cmd.

**Links:**
- A link within the page, to a section, a keyword or a data type, SHALL show its target in the page.
- `http`, `https` and `mailto` links SHALL open outside the viewer.
- `vscode:` and `vscode-insider:` links, and on desktop links of the product's own URL scheme, SHALL be handled by VS Code.
- `command:` links and links of other schemes SHALL do nothing.

**Content.** Scripts, event handlers and forms contained in documentation SHALL NOT run, and nothing in it SHALL navigate the viewer away from its page.

**Without Markdown support.** When VS Code's built-in Markdown support is disabled, the viewer SHALL show a notice and the page as plain Markdown text. The outline SHALL then list the keywords and data types; choosing one of them is not required to scroll or to add a history entry.

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

**Back and forward** SHALL be offered:
- as toolbar buttons;
- as the keys Alt+Left and Alt+Right, or Cmd+[ and Cmd+] on macOS, while the viewer has the focus;
- as the mouse's back and forward buttons.

While the viewer has the focus, these keys SHALL act only on the viewer.

**Find.** Ctrl+F, or Cmd+F on macOS, SHALL open a find bar that searches only the page, also while a keyboard layout without Latin letters is active. It SHALL show the number of matches and which one is current, and mark the matches, also in high contrast themes. Enter SHALL go to the next match and Shift+Enter to the previous one.
- It SHALL match the text as the page displays it: whitespace in the search text SHALL match any whitespace within a paragraph, heading, list item or table cell, such as a line break of the documentation source.
- While the find bar is open, a page that the viewer shows SHALL open where it would open without the find bar; the bar searches it again, and the first match in view becomes the current one.

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

"Show in New Documentation Viewer" and the second item action of the Keywords view SHALL always open a new viewer, also when a viewer is pinned; the new viewer is then the viewer used last.

At most one viewer SHALL be pinned; pinning one SHALL unpin the others. After a reload of the window, a restored viewer SHALL count for this choice only once its tab has been shown. A new viewer SHALL open beside the active editor, where the editor keeps the focus. When the setting `robotcode.documentationViewer.openLocation` is `active`, it SHALL open in the active editor group instead. A viewer in another window SHALL be brought to the front there. Navigation within a viewer SHALL stay in that viewer.

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

The last generated page of each target SHALL be kept per workspace folder, Python environment, selected profiles and these settings, also across restarts; at least the pages of the 50 most recently generated targets SHALL be kept.

Showing a target SHALL show its kept page at once, if there is one. It SHALL generate the page again in the background once per session, and update the view when the result differs. The refresh button SHALL generate it again. When a generation fails, the viewer SHALL show the error, above the kept page if there is one.

When documentation is shown at a keyword that the page does not have, for example a keyword added since the page was generated, the viewer SHALL generate the page again, once, and show it at the keyword if the new page has it.

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

On desktop, "Open Documentation", "Show Documentation" of the Keywords view, and output files opened with `robotcode.run.openOutputTarget` set to `simpleBrowser`, SHALL open in VS Code's integrated browser beside the editor. A later page SHALL reuse the tab that shows a page of the same documentation server. In VS Code for the Web, which has no integrated browser, they SHALL open in the Simple Browser as before.

#### Scenario: Two documentation pages on desktop
- **WHEN** the user runs "Open Documentation" on `Collections` and then on `BuiltIn` in desktop VS Code
- **THEN** `BuiltIn` is shown beside the editor, in the tab that showed `Collections`

#### Scenario: VS Code for the Web
- **WHEN** the user runs "Open Documentation" in a Codespace opened in VS Code for the Web
- **THEN** the page opens in the Simple Browser, as before
