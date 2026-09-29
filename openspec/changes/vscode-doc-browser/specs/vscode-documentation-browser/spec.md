# Spec Delta

## Purpose

Defines the Documentation Browser of the VS Code extension and how RobotCode opens documentation from the editor: the list of libraries, resource files and suite files, how their pages are generated, kept and refreshed, the page view, the documentation actions of the editor and the Keywords view, the import these actions document, and where Libdoc pages open.

## ADDED Requirements

### Requirement: Documentation actions in the editor

Wherever RobotCode offers "Open Documentation", it SHALL also offer the source action "Show in Documentation Browser", under the same conditions:
- on the name of a Library or Resource import;
- on a keyword reference in a keyword call, setup, teardown or template;
- on the name in a keyword definition header.

The offered actions and what they document SHALL be the same whether the semantic-model analysis path is enabled or not.

"Show in Documentation Browser" SHALL add the library, resource file or suite file to the browser's list when it is not in the list yet, open the browser beside the editor, show that entry and, for a keyword position, show the page at that keyword.

#### Scenario: Library import name
- **WHEN** source actions are requested with the cursor on `Collections` in `Library    Collections`
- **THEN** "Open Documentation" and "Show in Documentation Browser" are offered, both for the library `Collections`

#### Scenario: Keyword of a library that is not in the list
- **WHEN** the list contains only `BuiltIn` and the user chooses "Show in Documentation Browser" on a call of `Remove From List`
- **THEN** `Collections` is added to the list, and its page opens at `Remove From List`

#### Scenario: Keyword definition in a resource file
- **WHEN** source actions are requested on the name in a keyword definition header of a `.resource` file
- **THEN** both actions are offered, and "Show in Documentation Browser" shows that resource file at the keyword

#### Scenario: Keyword definition in a suite file
- **WHEN** source actions are requested on the name in a keyword definition header of a file with a `*** Test Cases ***` section
- **THEN** both actions are offered, and "Show in Documentation Browser" shows that suite file at the keyword

#### Scenario: Both analysis paths
- **WHEN** the same positions are evaluated with the semantic-model analysis path enabled and disabled
- **THEN** the offered actions and what they document are identical

### Requirement: Documentation actions document the import the analysis used

The documentation actions of the editor and the Keywords view SHALL document the import through which the analysis resolved the name at the cursor:
- Variables in the import name and arguments SHALL be replaced with the values the analysis knows; the arguments SHALL be passed as strings.
- A relative path in the import SHALL be resolved against the directory of the file that contains the import, also when that file is a resource file imported by the current document, and `${CURDIR}` SHALL be that directory.
- For a keyword call with a library or resource prefix (`lib_var.A Library Keyword`), the import SHALL be the one the prefix names. When the same library is imported twice with different arguments, a call through the second import's alias SHALL use the second import's arguments.
- A library imported by module name, such as `BuiltIn` or `Collections`, SHALL be the same browser entry wherever it was shown from.

#### Scenario: Resource imported through a resource in another directory
- **WHEN** a suite imports `sub/local.resource`, which imports `deeper/nested.resource`, and documentation is opened on a call of a keyword of `nested.resource` in the suite
- **THEN** "Open Documentation" and the Documentation Browser both show `nested.resource`

#### Scenario: Second import of the same library
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello` and with `a_param=${LIB_ARG}` as `lib_var`, `${LIB_ARG}` is `from lib`, and documentation is opened on `lib_var.A Library Keyword`
- **THEN** the documentation is generated with the argument `a_param=from lib`
- **AND** on `lib_hello.A Library Keyword` it is generated with `a_param=from hello`, also when the analysis of the suite was restored from the cache

#### Scenario: Module library from two directories
- **WHEN** the user chooses "Show in Documentation Browser" on `Library    Collections` in two suites in different directories
- **THEN** the list contains one `Collections` entry

### Requirement: The Keywords view opens documentation at the keyword

Each import and keyword item of the Keywords view SHALL offer "Show in Documentation Browser", for the same import as the documentation actions of the editor. "Show Documentation" and "Show in Documentation Browser" on a keyword defined in the current document SHALL open the documentation at that keyword.

#### Scenario: Local keyword with "Show Documentation"
- **WHEN** the user chooses "Show Documentation" on a keyword of the current file in the Keywords view
- **THEN** the Libdoc page opens at that keyword

#### Scenario: Library import item
- **WHEN** the user chooses "Show in Documentation Browser" on the import item `lib_hello` of `alibrary`
- **THEN** the browser shows `alibrary` generated with the argument `a_param=from hello`

### Requirement: The browser keeps a list that the user manages

The Documentation Browser SHALL list `BuiltIn` and the entries the user added, and nothing else. `BuiltIn` SHALL always be in the list and SHALL NOT be removable. The user SHALL be able to add an entry by hand, as a library name with optional import arguments (`Name::arg1::arg2`) or as the path of a library, resource or suite file, and from the editor or the Keywords view. Adding an entry that is already in the list SHALL show the existing entry. The user SHALL be able to remove an entry. The list SHALL be kept across restarts of VS Code for the workspace, and SHALL NOT be written to settings or project files. In a workspace with several folders, each entry SHALL belong to one folder, and each folder SHALL have its own `BuiltIn` entry.

#### Scenario: First use in a workspace
- **WHEN** the browser is opened for the first time in a workspace
- **THEN** the list contains only `BuiltIn`

#### Scenario: Adding by hand
- **WHEN** the user adds `alibrary::a_param=x`
- **THEN** the list contains an entry for `alibrary`, generated with the argument `a_param=x`
- **AND** the entry is still in the list after VS Code was restarted, and no settings file was changed

#### Scenario: Removing an entry
- **WHEN** the user removes an entry that was added before
- **THEN** it is no longer in the list, while `BuiltIn` offers no removal

### Requirement: Pages are generated live and kept

The page of an entry SHALL be what `robotcode doc lib` produces for the entry, run in the Python environment that RobotCode uses for the entry's workspace folder, with the folder's selected profiles, the settings `robotcode.robot.pythonPath`, `robotcode.robot.languages`, `robotcode.robot.variables`, `robotcode.robot.variableFiles` and `robotcode.robot.env`, and, for an entry added from the editor, the directory the import is resolved against. The last generated page of each entry SHALL be kept per workspace folder and Python environment, also across restarts. Opening an entry SHALL show its kept page at once, if there is one, generate the page again in the background, and update the view when the result differs. The user SHALL be able to refresh one entry and all entries. When a generation fails, the view SHALL show the error and keep the last good page.

#### Scenario: Kept page
- **WHEN** the user opens an entry that was generated before
- **THEN** the kept page is shown at once, and it is replaced when the new generation gives a different result

#### Scenario: Profile variable in the import arguments
- **WHEN** the entry `MyLib::${URL}` is generated and the profile selected in `robotcode.profiles` sets `URL`
- **THEN** the page shows the library as initialised with the profile's value of `URL`

#### Scenario: Language from the settings
- **WHEN** `robotcode.robot.languages` is `["de"]`, `robot.toml` and the profiles set no languages, and the user adds a resource file with the headers `*** Einstellungen ***` and `*** Schlüsselwörter ***` and no `Language:` line, on Robot Framework 6.0 or newer
- **THEN** the page lists the keywords of the file

#### Scenario: Import arguments that fail
- **WHEN** the library of an entry cannot be initialised with the entry's arguments, and a page of the entry was kept before
- **THEN** the view shows the error together with the kept page

#### Scenario: Refresh all
- **WHEN** the user chooses to refresh all entries
- **THEN** every entry of the list is generated again

#### Scenario: Markdown-documented library without Python-Markdown
- **WHEN** the browser shows `BuiltIn` on Robot Framework 7.5 in an environment without the `markdown` package
- **THEN** the full documentation is shown

### Requirement: The page view

The browser SHALL show, in the layout of Libdoc, a sidebar with the list, a search field and the keyword list of the selected entry, and next to it the page of the selected entry. The search SHALL keep the keywords whose name, documentation or tags contain the search text, ignoring case. Choosing a keyword in the keyword list SHALL show the page at that keyword. A link within the page, to a section, a keyword or a data type, SHALL show its target in the page. `http`, `https` and `mailto` links SHALL open outside the browser, and `vscode:` links SHALL be handled by VS Code as in its Markdown preview; `command:` links and all other links SHALL do nothing. Scripts, event handlers and forms contained in documentation SHALL NOT run. The browser SHALL load its own scripts and styles only from the extension, and SHALL follow the VS Code color theme. It SHALL work on desktop, in remote windows, and in VS Code for the Web with a remote extension host, for example a Codespace.

#### Scenario: Search
- **WHEN** the user types `dictionary` into the search field while `Collections` is selected
- **THEN** only keywords whose name, documentation or tags contain `dictionary`, ignoring case, remain in the keyword list

#### Scenario: Links in the introduction
- **WHEN** the user clicks the entry `String representations` of the table of contents, or the link `Should Be Equal`, in the introduction of `BuiltIn` on Robot Framework 7.5
- **THEN** the page scrolls to that section or keyword

#### Scenario: Link to a data type
- **WHEN** the user clicks the link `Element` in the documentation of `Parse Xml` of `XML` on Robot Framework 7.5
- **THEN** the page scrolls to the heading of the data type `Element`

#### Scenario: Script in documentation
- **WHEN** a library documented in HTML format contains a `<script>` element
- **THEN** the element is not executed

#### Scenario: Theme change
- **WHEN** the user switches from a light to a dark color theme while the browser is open
- **THEN** the sidebar and the page follow the new theme

#### Scenario: Remote window
- **WHEN** the browser is used in a window connected to WSL, SSH or a dev container
- **THEN** it lists, generates and shows pages as in a local window

### Requirement: Libdoc pages open beside the editor

When VS Code has its integrated browser, "Open Documentation", "Show Documentation" of the Keywords view and output files opened with `robotcode.run.openOutputTarget` set to `simpleBrowser` SHALL open in the integrated browser beside the editor. On VS Code 1.114 or later, a later page SHALL reuse the tab that shows a page of the same documentation server. Without the integrated browser they SHALL open in the Simple Browser as before.

#### Scenario: Two documentation pages on desktop
- **WHEN** the user runs "Open Documentation" on `Collections` and then on `BuiltIn` in desktop VS Code 1.114 or later
- **THEN** `BuiltIn` is shown beside the editor, in the tab that showed `Collections`

#### Scenario: VS Code for the Web
- **WHEN** the user runs "Open Documentation" in a Codespace opened in VS Code for the Web
- **THEN** the page opens in the Simple Browser, as before
