# Spec Delta

## Purpose

Defines how RobotCode opens the documentation of libraries, resource files and the current document in VS Code. This covers the navigation target computed for the documentation actions, the language server request that resolves a target the way the analysis does, the documentation browser panel with its layout, navigation, refresh and offline rendering, and its entry points in the Keywords tree view.

## ADDED Requirements

### Requirement: Documentation actions share one target

For every position where a documentation action is offered, RobotCode SHALL compute one documentation target and offer two source actions from it:
- "Open Documentation", which opens Robot Framework's Libdoc HTML;
- "Open in Documentation Browser", which opens the documentation browser.

The target SHALL be editor-neutral and consist of:
- a kind: `library`, `resource` or `document`;
- the import name and the import arguments as written;
- the alias;
- the base directory;
- the URI of the context document, or of a workspace folder when no document is the context;
- an optional anchor, with a kind of `keyword`, `section`, `type` or `init`, and a name.

Targets SHALL be computed for these positions:

| Cursor position | Target |
|---|---|
| The name of a Library import | The library |
| An argument of a Library import | The library, with an anchor on its importing section |
| The name of a Resource import | The resource file |
| A keyword reference in a keyword call, setup, teardown or template | The library or resource file that owns the keyword, with the keyword as anchor |
| A keyword definition header | The current document, with that keyword as anchor |

A keyword owned by the current document SHALL target the current document. Positions on Variables imports SHALL produce no documentation action. The actions SHALL be offered under the same conditions as "Open Documentation" before this change: import and keyword-reference positions only when source actions are requested, keyword references only for an empty selection, and definition headers without either restriction. The results SHALL be identical whether the semantic-model analysis path is enabled or not.

#### Scenario: Library import name
- **WHEN** source actions are requested with the cursor on `Collections` in `Library    Collections`
- **THEN** "Open Documentation" and "Open in Documentation Browser" are offered, both for the library `Collections` without anchor

#### Scenario: Library import argument
- **WHEN** source actions are requested with the cursor on `a_param=from hello` in `Library    alibrary    a_param=from hello    WITH NAME    lib_hello`
- **THEN** both actions are offered for the library `alibrary` with the arguments `a_param=from hello`, the alias `lib_hello` and an anchor on the importing section

#### Scenario: Keyword of a library
- **WHEN** source actions are requested with the cursor on `Log To Console` in a test
- **THEN** both actions are offered for the library `BuiltIn` with the keyword anchor `Log To Console`

#### Scenario: Keyword definition header
- **WHEN** source actions are requested with the cursor on the name in the header of a keyword defined in the current file
- **THEN** both actions are offered for the current document with that keyword as anchor

#### Scenario: Variables import
- **WHEN** source actions are requested with the cursor on the name of a `Variables` import
- **THEN** no documentation action is offered

#### Scenario: Both analysis paths
- **WHEN** the same positions are evaluated with the semantic-model flag on and off
- **THEN** the offered actions and their targets are identical

### Requirement: A target identifies the import the analysis used

The base directory of a target SHALL be the directory of the file that contains the import: for a library or resource imported through a resource file, the directory of that resource file. For a default library such as `BuiltIn`, which has no import, it SHALL be the directory of the current document. For a keyword call, the target SHALL describe the import that the keyword was resolved through, with its arguments and alias; for a call with a library or resource prefix (`lib_var.A Library Keyword`), that is the import the prefix names. When the same library is imported twice with different arguments or aliases, a call through the second import's alias SHALL target the second import. "Open Documentation" SHALL use the same base directory and arguments. For an argument of a Library import, its URL SHALL point to the `Importing` section of the Libdoc page.

#### Scenario: Library imported by relative path through a resource in another directory
- **WHEN** a suite imports `sub/local.resource`, which imports `Library    ./local_lib.py` located next to it, and the documentation of a keyword from `local_lib.py` is opened from the suite
- **THEN** the target's base directory is the directory of `local.resource`
- **AND** both the documentation browser and the Libdoc page show `local_lib`

#### Scenario: Second import of the same library
- **WHEN** a suite imports `alibrary` twice, once with `a_param=from hello` and alias `lib_hello` and once with `a_param=${LIB_ARG}` and alias `lib_var`, and the documentation is opened on `lib_var.A Library Keyword`
- **THEN** the target carries the arguments `a_param=${LIB_ARG}` and the alias `lib_var`
- **AND** on `lib_hello.A Library Keyword` the target carries `a_param=from hello` and `lib_hello`, also when the analysis of the suite was restored from the cache

#### Scenario: Two aliases with the same arguments
- **WHEN** a suite imports `alibrary    a_param=x` twice, with the aliases `first` and `second`, and the documentation is opened on `second.A Library Keyword`
- **THEN** the target carries the alias `second`

### Requirement: The documentation request resolves a target like the analysis

The language server SHALL answer the request `robot/documentation/getDocument` with a documentation page for a target, or with no result when the target cannot be resolved. Resolution SHALL depend on the kind of target:
- A library or resource target with a context document SHALL resolve to the documentation that the analysis of the context document holds for the import with the same name, arguments, alias and base directory, without loading the library again.
- A target without such an import SHALL be resolved through the analysis's import handling, with the context document's variables when the context document is known, including the analysis cache and the configured load timeout. A target whose context is a workspace folder SHALL be resolved through that folder's import handling, with the configured variables only.
- A `document` target SHALL resolve to the documentation of the context document as currently edited, including unsaved changes.

A library or resource that could not be loaded SHALL still produce a page: it shows the load errors and whatever documentation is available. The page SHALL contain:
- the canonical library documentation Markdown of the documentation, as defined by the capability `library-documentation-markdown`, unchanged;
- its navigation outline;
- for each keyword of the outline, its tags, its deprecation state, its short documentation and its source location when known;
- the load errors with their source locations;
- the outline entry that the target's anchor resolved to, if any.

#### Scenario: Library with import arguments
- **WHEN** the browser opens `alibrary` with the arguments and base directory of an import in the current suite
- **THEN** the page shows the keywords that the analysis reports for that import
- **AND** the library is not loaded again when the analysis already holds its documentation

#### Scenario: Unsaved keyword in the current document
- **WHEN** a keyword is added to the open file without saving, and the browser is opened on its definition header
- **THEN** the page lists the new keyword and scrolls to it

#### Scenario: Library that fails to load
- **WHEN** the browser opens a library whose import raises an error
- **THEN** a page is shown with the error message and its source location in the importing section

#### Scenario: Workspace folder as context
- **WHEN** the request names the library `Collections` with no arguments, the workspace folder's path as base directory and the workspace folder's URI as context
- **THEN** the page shows the documentation of `Collections`

#### Scenario: Unknown context document
- **WHEN** the request names a context document the language server does not know and the target is of kind `document`
- **THEN** the request returns no result and the browser reports that the documentation is not available

### Requirement: Navigation uses semantic anchors

A `keyword` anchor SHALL match the keyword whose name is equal after Robot Framework's normalization, ignoring case, spaces and underscores. For a keyword with embedded arguments, the anchor is the name as defined. When several keywords match, the first in page order SHALL be selected. A `section` anchor SHALL match a top-level section (Introduction, Importing, Keywords, Data types) or an introduction heading by title. A `type` anchor SHALL match a data type by name. An `init` anchor SHALL select the importing section. An anchor without a match, including a keyword that the canonical documentation leaves out as private, SHALL open the page at its top. Clicking an in-page link SHALL navigate within the page. Links with the `http`, `https` or `mailto` scheme SHALL open outside the editor. Other links SHALL do nothing. Keywords and load errors with a known source location SHALL offer to open that location in the editor. The browser SHALL keep a back/forward history of the pages and anchors shown.

#### Scenario: Keyword anchor with different spelling
- **WHEN** the browser opens `BuiltIn` with the keyword anchor `log_to_console`
- **THEN** the page scrolls to `Log To Console`

#### Scenario: Anchor without match
- **WHEN** the anchor names a keyword the library does not have
- **THEN** the page opens at the top

#### Scenario: Reference link in Markdown documentation
- **WHEN** the user clicks the link to `Set Log Level` in the documentation of `Log` on RF 7.5
- **THEN** the page scrolls to `Set Log Level`, and back returns to `Log`

#### Scenario: Go to source
- **WHEN** the user chooses to open the source of a keyword defined in a resource file
- **THEN** that file opens in the editor at the keyword's line

### Requirement: One browser panel beside the editor

The documentation browser SHALL be a single panel. Opening a target SHALL replace the panel's page. The panel SHALL open beside the active editor on first use and keep the focus in the editor. Its sidebar SHALL list:
- the Introduction and its headings;
- Importing, when the canonical documentation has that section;
- Keywords, with their count and a filter on name and tags;
- Data types, when the canonical documentation has that section;
- the keyword tags, where choosing a tag filters the keywords.

The panel SHALL show a loading state while a request is running. A newer request SHALL supersede an older one. The panel SHALL offer a refresh action. A page for a `document` target SHALL also be refreshed automatically when that document changes while the panel is visible. Opening the same target again SHALL request the page again.

#### Scenario: Opening a second target
- **WHEN** the browser shows `BuiltIn` and the user opens the documentation of `Collections`
- **THEN** the same panel shows `Collections`, and the editor keeps the focus

#### Scenario: Filtering keywords
- **WHEN** the user types `list` into the keyword filter of `Collections`
- **THEN** only keywords whose names or tags contain `list` (ignoring case and spaces) remain in the sidebar, and the count reflects the filter

#### Scenario: Editing the current document
- **WHEN** the browser shows the current document and the user changes a keyword's documentation
- **THEN** the page shows the changed documentation without a manual refresh

### Requirement: The browser works offline and follows the VS Code theme

The browser SHALL load its scripts and styles only from the extension. It SHALL NOT load anything from the network, except images that the documentation itself references. It SHALL use VS Code's theme colors and fonts, and it SHALL NOT need the optional Python-Markdown package. Only the browser's own scripts SHALL run: script content that the documentation contains SHALL NOT run.

#### Scenario: No network
- **WHEN** the browser opens `BuiltIn` on RF 7.5 without network access and without Python-Markdown installed
- **THEN** the full documentation is shown

#### Scenario: Theme change
- **WHEN** the user switches from a light to a dark color theme while the browser is open
- **THEN** the page follows the new theme

#### Scenario: Script in documentation
- **WHEN** a library documented in HTML format contains a `<script>` element
- **THEN** the element is not executed

### Requirement: Keywords tree view opens the browser

Each import and keyword item in the Keywords tree view SHALL offer "Open in Documentation Browser". It SHALL use the same target as the documentation actions would for that import or keyword. "Show Documentation" and "Open in Documentation Browser" on a keyword defined in the current document SHALL navigate to that keyword.

#### Scenario: Local keyword in the tree view
- **WHEN** the user chooses "Show Documentation" or "Open in Documentation Browser" on a keyword of the current file in the Keywords tree view
- **THEN** the documentation opens at that keyword

#### Scenario: Library import in the tree view
- **WHEN** the user chooses "Open in Documentation Browser" on the `alibrary` import item with alias `lib_hello`
- **THEN** the browser shows `alibrary` as loaded with the arguments of that import
