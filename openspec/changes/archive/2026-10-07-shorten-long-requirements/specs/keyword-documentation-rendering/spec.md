# Spec Delta

## MODIFIED Requirements

### Requirement: Argument descriptions are rendered with the signature

When a keyword has documented arguments, the rendered keyword documentation SHALL show the argument table with an additional column for the descriptions, so that every argument is named once, with its type, its default value and its description.
- An argument without a description SHALL have an empty description cell.
- A name that the documentation describes without being an argument of the keyword SHALL get a row of its own, with its name and its description and the other cells empty.

#### Scenario: Standard-library keyword on RF 7.5
- **WHEN** the hover for `Log` (BuiltIn) is shown on RF 7.5
- **THEN** the arguments are shown in a table with a row for `message` with its type `object` and "The message to log.", and a row for `level` with its type, the default `INFO` and "The log level to use."
- **AND** no argument is named twice, and the documentation text below contains no `Args:` block

#### Scenario: Same keyword on RF 7.4 and RF 7.5
- **WHEN** the hover for `Log` (BuiltIn) is shown on RF 7.4 and on RF 7.5
- **THEN** both show the arguments in a table, one row per argument, and only the one on RF 7.5 has the description column

#### Scenario: Description with a list
- **WHEN** a keyword documents an argument as "What to paint:" followed by the list items "walls" and "doors"
- **THEN** the description cell of that argument shows "What to paint:", "- walls" and "- doors", each starting a new line within the cell
- **AND** every row of the table has as many cells as the other rows

#### Scenario: Documented name that is no argument
- **WHEN** a keyword documents `timeout` in its `Args:` section without having such an argument
- **THEN** the table has a row for `timeout` with its description, and its type and default cells are empty

#### Scenario: Keyword with return and raises documentation
- **WHEN** a keyword documents `Returns:` and `Raises:` sections on RF 7.5
- **THEN** the rendered documentation shows the return description next to the return type and a `Raises` list with each exception and its description

#### Scenario: Keyword without descriptions in a non-Markdown library
- **WHEN** a keyword of a library documented in Robot, reStructuredText, HTML or plain-text format has no Google-style sections, or the installed Robot Framework is older than 7.5
- **THEN** its hover is identical to the hover before this change, apart from escaped `|` characters in Robot-format table cells, link targets without a `\#` escape, and in VS Code the links to the Documentation Viewer

#### Scenario: Markdown library on an older Robot Framework
- **WHEN** a library declares `ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"` and is documented on RF 7.4
- **THEN** its documentation is normalised (reference links, headings, table of contents, admonitions) like on RF 7.5, without argument descriptions

### Requirement: Markdown reference links are resolved

In documentation declared as Markdown, reference-style links (`[Name]`, `[Name][]`, `[text][Name]`) whose target is a keyword of the same library, a type used by the library, a section of the library introduction or one of Libdoc's default targets (introduction, importing, keywords) SHALL NOT be rendered as literal brackets. Links inside code spans and fenced code blocks, images and unknown targets SHALL be left unchanged. Matching SHALL ignore case and spaces, as Libdoc does.

#### Scenario: Keyword reference in a hover
- **WHEN** the hover for `Log` is shown on RF 7.5 to a language client other than the VS Code extension
- **THEN** `[Set Log Level]` is rendered as `` `Set Log Level` `` and `[String representations]` as `` `String representations` ``

#### Scenario: Keyword reference in a full-document view
- **WHEN** `robotcode doc lib BuiltIn` is run on RF 7.5
- **THEN** `[Set Log Level]` is rendered as the link `[Set Log Level](#set-log-level)`

#### Scenario: Type reference in a full-document view
- **WHEN** `robotcode doc lib OperatingSystem` is run on RF 7.5
- **THEN** `[Secret]` in the argument description of `Set Environment Variable` is rendered as the link `[Secret](#secret-standard)` to the heading `Secret (Standard)` in the `Data types` section
- **AND** `robotcode doc keyword OperatingSystem "Set Environment Variable"` renders it as `` `Secret` ``

#### Scenario: Introduction-defined link in a keyword
- **WHEN** a keyword documentation uses `[VAR syntax]` and the library introduction defines `[VAR syntax]: https://…`
- **THEN** the keyword hover renders it as a link to that URL

#### Scenario: Reference in the REPL keyword view
- **WHEN** `.kw Log` is shown in the REPL on RF 7.5
- **THEN** `[Set Log Level]` is a navigable link to that keyword's documentation

#### Scenario: Brackets in code are untouched
- **WHEN** a documentation contains `` `[Tags]` `` in a code span or `[1]` with a keyword-local definition
- **THEN** they are rendered unchanged

#### Scenario: Keyword reference in a VS Code hover
- **WHEN** the hover for `Log` is shown in VS Code on RF 7.5
- **THEN** `Set Log Level` and `String representations` are links that show `BuiltIn` in the Documentation Viewer at that keyword and that section

### Requirement: Markdown library introductions are normalised

For libraries documented in Markdown, a `%TOC%` line in the introduction SHALL be replaced by a two-level table of contents of the introduction's headings; ATX headings SHALL be shifted one level down (`#` → `##`) as Robot-format headings are today; GitHub-style admonitions (`> [!NOTE]`, `> [!WARNING]`, …) SHALL be rendered as block quotes with a bold label; fenced code, tables and raw HTML SHALL be left unchanged.

#### Scenario: BuiltIn library hover on RF 7.5
- **WHEN** the hover for the `BuiltIn` library import is shown on RF 7.5
- **THEN** it contains no literal `%TOC%`, no line starting with a single `# `, and a table of contents listing the introduction sections

#### Scenario: Admonition in a keyword documentation
- **WHEN** a Collections keyword documentation contains `> [!WARNING]` on RF 7.5
- **THEN** the hover shows a block quote starting with **Warning** and no literal `[!WARNING]`

### Requirement: Robot-format tables and links convert to valid Markdown

When documentation in Robot Framework's format is converted to Markdown, on every surface and every supported Robot Framework version, a `|` inside the content of a table cell SHALL be escaped, so that every table row keeps the number of cells Robot Framework gives it. No link target SHALL contain the escaped `\#`: links converted from Robot-format links and URLs, and the links from backtick names to headings of the same documentation, SHALL be written with `#`.

#### Scenario: Pipe inside a table cell
- **WHEN** the hover for `Should Match Regexp` (BuiltIn) is shown on RF 6.1
- **THEN** the example table row containing `(Foo|Bar)` has as many cells as the header row of its table

#### Scenario: Link with a fragment
- **WHEN** a Robot-format keyword documentation contains `[http://example.com/x.html#frag|docs]`
- **THEN** the rendered documentation contains the link `[docs](http://example.com/x.html#frag)`

#### Scenario: Library introduction on an older Robot Framework
- **WHEN** the hover for a `BuiltIn` import is shown on RF 6.1 in a language client other than the VS Code extension
- **THEN** it contains the links `[eval](http://docs.python.org/library/functions.html#eval)` and `[str](#str)`
- **AND** no link target contains `\#`

## ADDED Requirements

### Requirement: Description cells of the argument table

A description SHALL be written into its cell as one line: a line break within a paragraph SHALL become a space, and each further paragraph and each list item SHALL start a new line within the cell (`<br>`). A `|` in a description SHALL be escaped, so that every row has the same number of cells. A keyword without argument descriptions SHALL keep the argument table without the description column.

#### Scenario: Line break within a paragraph
- **WHEN** a keyword documents an argument with the paragraph "The first line" followed by the line "of the description"
- **THEN** its description cell shows "The first line of the description" on one line

### Requirement: Return and raises descriptions

When a return description exists it SHALL be shown with the return type (`**Return Type**: \`T\` — description`, or `**Returns**: description` without a type); on the full page, the names in `T` link to their data types by the requirement "Data types" of `library-documentation-markdown`. Raised exceptions SHALL be listed with their descriptions.

#### Scenario: Return description without a return type
- **WHEN** a keyword without a return type documents a `Returns:` section on RF 7.5
- **THEN** the rendered documentation shows `**Returns**:` followed by the description

### Requirement: Keywords without descriptions render as before

Outside the full-page documentation of `library-documentation-markdown`, keywords whose documentation is not in Markdown format and has no argument, return or raises description SHALL render exactly as before, except for the corrections of the requirement "Robot-format tables and links convert to valid Markdown" and, in VS Code, the links of the requirement "Links in documentation open the Documentation Viewer" of `vscode-documentation-viewer`.

#### Scenario: reStructuredText keyword without sections
- **WHEN** the hover of a keyword of a library in reStructuredText format without Google-style sections is shown on RF 7.5 in a language client other than the VS Code extension
- **THEN** it renders exactly as before, apart from the corrections of the requirement "Robot-format tables and links convert to valid Markdown"

### Requirement: Reference links in keyword views

In hover, signature help and completion, in the output of `robotcode doc keywords` and `robotcode doc keyword`, and in the `doc` and `short_doc` fields of the JSON output of `robotcode doc`, resolved reference links SHALL be rendered as inline code; in VS Code, in hover, signature help, completion and the tooltips of the Keywords view, they SHALL be links to the Documentation Viewer by the requirement "Links in documentation open the Documentation Viewer" of `vscode-documentation-viewer`.

#### Scenario: Keyword reference in the keyword documentation command
- **WHEN** `robotcode doc keyword BuiltIn Log` is run on RF 7.5
- **THEN** `[Set Log Level]` is rendered as `` `Set Log Level` ``

### Requirement: Reference links in full-document views

In full-document views (REPL `.doc`, `robotcode doc lib` and `browse`, Markdown documentation view), resolved reference links SHALL be rendered as in-document links, where a reference to a type links to the type's heading in the `Data types` section, by the requirement "Data types" of `library-documentation-markdown`. In the REPL keyword view they SHALL be rendered as navigable keyword links.

#### Scenario: Keyword reference in the REPL documentation
- **WHEN** `.doc BuiltIn` is shown in the REPL on RF 7.5
- **THEN** `[Set Log Level]` is an in-document link to the heading of `Set Log Level`

### Requirement: Reference definitions of the library introduction

Reference definitions declared in the library introduction SHALL be applied to keyword documentation.

#### Scenario: Definition from the introduction
- **WHEN** the introduction of a Markdown library defines `[docs]: https://example.com/docs` and a keyword documentation uses `[docs]`
- **THEN** the keyword hover renders `docs` as a link to `https://example.com/docs`

### Requirement: No backtick auto-linking in Markdown documentation

The backtick auto-linking applied to Robot-format documentation SHALL NOT be applied to Markdown documentation.

#### Scenario: Keyword name in backticks
- **WHEN** a keyword documentation of a Markdown library contains `` `Log` `` and is shown on the full page
- **THEN** `Log` is rendered as inline code, not as a link

### Requirement: Other Robot-format text converts as before

Link texts and all other text SHALL be converted as before, apart from the names in single backticks that the full page links (requirement "Names in Robot-format documentation" of `library-documentation-markdown`) and, in VS Code, the links of the requirement "Links in documentation open the Documentation Viewer" of `vscode-documentation-viewer`, which replace these links there.

#### Scenario: Link text
- **WHEN** a Robot-format keyword documentation contains `[http://example.com|example]`
- **THEN** the rendered documentation contains the link `[example](http://example.com)`
