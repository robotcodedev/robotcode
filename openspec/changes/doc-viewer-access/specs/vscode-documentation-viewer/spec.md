# Spec Delta: vscode-documentation-viewer

## MODIFIED Requirements

### Requirement: Documentation actions in the editor

RobotCode SHALL offer the source actions "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Open Documentation (deprecated)", in this order, under the same conditions:
- on the name of a Library or Resource import;
- on a keyword reference in a keyword call, setup, teardown or template;
- on the name in a keyword definition header.

The offered actions and what they document SHALL be the same whether the semantic-model analysis path is enabled or not.

"Show in Documentation Viewer" SHALL show the documentation of that library, resource file or suite file in the viewer chosen by the requirement "Which viewer shows documentation from the editor". "Show in New Documentation Viewer" SHALL show it in a new viewer. For a keyword position, both SHALL show the page at that keyword. "Open Documentation (deprecated)" SHALL open the Libdoc page, at the keyword for a keyword position.

"Show in Documentation Viewer" SHALL be the preferred source action; the other two SHALL NOT. While the editor of a Robot Framework file has the focus, Shift+F1 (⇧F1 on macOS) SHALL run the preferred source action at the cursor, without a menu, and the source action menu SHALL show the key next to "Show in Documentation Viewer". Where the cursor offers no documentation, the key SHALL open nothing, and VS Code SHALL report that no preferred source action is available.

#### Scenario: Library import name
- **WHEN** source actions are requested with the cursor on `Collections` in `Library    Collections`
- **THEN** the menu lists "Show in Documentation Viewer" with Shift+F1, "Show in New Documentation Viewer" and "Open Documentation (deprecated)", in this order, all for the library `Collections`

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

#### Scenario: Key on a keyword
- **WHEN** the cursor is on a call of `Remove From List` and the user presses Shift+F1
- **THEN** a viewer shows `Collections` at `Remove From List`, no menu is shown, and the editor keeps the focus

#### Scenario: Key without documentation
- **WHEN** the cursor is in a comment and the user presses Shift+F1
- **THEN** no viewer opens or changes, and VS Code reports that no preferred source action is available

### Requirement: Documentation actions document the import the analysis used

The documentation actions of the editor and the Keywords view, and the links of a hover, SHALL document the import through which the analysis resolved the name at the cursor:
- Variables in the import name and arguments SHALL be replaced with the values the analysis knows; the arguments SHALL be passed as strings.
- A relative path in the import SHALL be resolved against the directory of the file that contains the import, also when that file is a resource file imported by the current document, and `${CURDIR}` SHALL be that directory.
- For a keyword call with a library or resource prefix (`lib_var.A Library Keyword`), the import SHALL be the one the prefix names. When the same library is imported twice with different arguments, a call through the second import's alias SHALL use the second import's arguments.
- For a keyword call without a prefix, the import SHALL be the one the analysis resolved the call to, also when the same library is imported twice with different arguments and the library search order or the keywords of the two imports decide.
- A library imported by module name, such as `BuiltIn` or `Collections`, SHALL be shown with the same target wherever it was shown from.

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
- a book button titled "Show in Documentation Viewer", which SHALL do what "Show in Documentation Viewer" does;
- in its context menu, in this order: "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Show Documentation (deprecated)". "Show Documentation (deprecated)" SHALL open the Libdoc page, as the requirement "Libdoc pages open beside the editor" describes.

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

### Requirement: Libdoc pages open beside the editor

On desktop, "Open Documentation (deprecated)", "Show Documentation (deprecated)" of the Keywords view, and output files opened with `robotcode.run.openOutputTarget` set to `simpleBrowser`, SHALL open in VS Code's integrated browser beside the editor. A later page SHALL reuse the tab that shows a page of the same documentation server. In VS Code for the Web, which has no integrated browser, they SHALL open in the Simple Browser as before.

#### Scenario: Two documentation pages on desktop
- **WHEN** the user runs "Open Documentation (deprecated)" on `Collections` and then on `BuiltIn` in desktop VS Code
- **THEN** `BuiltIn` is shown beside the editor, in the tab that showed `Collections`

#### Scenario: VS Code for the Web
- **WHEN** the user runs "Open Documentation (deprecated)" in a Codespace opened in VS Code for the Web
- **THEN** the page opens in the Simple Browser, as before

## ADDED Requirements

### Requirement: The heading of the hover links to the Documentation Viewer

In VS Code, the first heading of a hover SHALL be a link to the Documentation Viewer where the hover shows a keyword, a library or a resource file and the documentation actions have a target:
- On a keyword reference in a keyword call, setup, teardown or template, and on the name in a keyword definition header, the link SHALL do what "Show in Documentation Viewer" does at that position: show the page at that keyword.
- On the name of a Library or Resource import, the link SHALL do what "Show in Documentation Viewer" does there.
- On the alias of a Library import, and on the library or resource prefix of a keyword call, where the hover shows the library or resource file, the link SHALL show the page of that import without going to a keyword.

The link SHALL show the documentation in the viewer chosen by the requirement "Which viewer shows documentation from the editor", for the import named by the requirement "Documentation actions document the import the analysis used". The heading SHALL keep its text and stay a heading, and its tooltip SHALL be "Show in Documentation Viewer".

The hover SHALL have no link where there is no such target: on a Variables import and on a call that matches several keywords. The hover of a variable or a test case SHALL have no link. Language clients other than the VS Code extension, such as the IntelliJ plugin, SHALL get the hover without links.

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
- in a completion item, the import the item comes from: for a keyword the import of that keyword, for a library or resource the item itself, and for a library name or resource path in an import, that library or file without import arguments; for a named argument or a value of an argument, the import of the called keyword, or the library of the import whose arguments are completed;
- in signature help, the import of the keyword whose signature is shown, also for the outer keyword of `Run Keyword` and its variants, or the library of the import whose arguments are shown;
- in a tooltip of the Keywords view, the import of the item, or the current file for its own keywords.

Variables imports and their files have no target. In documentation with a target:
- The first heading of the documentation of a keyword, a library or a resource file in a completion item and in the tooltip of an import SHALL be a link, as the heading of a hover is.
- A name that refers to a keyword, a data type or a section of the same library or resource file, in its documentation, in the description of an argument, a return value or an exception, written as a name in single backticks in Robot Framework's format or as a Markdown reference link, SHALL be a link that shows the page at that keyword, data type or section.
- A type in the argument table or in the return type that has a heading in `Data types` of the page SHALL be a link that shows the page at that data type.
- A link to a place in the documentation itself (`#…`), such as an entry of a table of contents or a link of the documentation's author, in Markdown or in HTML, SHALL show the page at that place.

Each link SHALL show the page in the viewer chosen by the requirement "Which viewer shows documentation from the editor", for the import named by the requirement "Documentation actions document the import the analysis used", and SHALL add a history entry. The links SHALL keep their text, code SHALL stay unchanged, and their tooltip SHALL be "Show in Documentation Viewer". A name without a heading on the page, such as a private keyword, a name of another library or a default section the page does not have, SHALL stay inline code. When the links would make the documentation longer than the 100,000 characters that VS Code shows, it SHALL keep only the link of its heading, with references as inline code and links to `#…` as text.

When the page does not have the keyword, data type or place, for example one added since the page was generated, the viewer SHALL generate the page again, once, and show it there if the new page has it, and otherwise from its start. Without VS Code's Markdown support, the viewer is not required to scroll there.

In documentation without a target, VS Code SHALL show links to a place in the documentation itself as text. Language clients other than the VS Code extension SHALL get all documentation as before: references as inline code and links to `#…` as they are.

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

The toolbar of a viewer SHALL have the button "Open as Markdown", after the refresh button. Choosing it SHALL open the Markdown of the page the viewer shows, as `robotcode doc lib` produced it, as a new untitled Markdown document in the viewer's editor group, with the focus. Saving the document SHALL ask for a file name. The viewer SHALL keep its target, position and history. While the viewer shows no page, such as while the first page of a target is generated or after a generation failed without a kept page, the button SHALL be disabled, also for the keyboard.

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
