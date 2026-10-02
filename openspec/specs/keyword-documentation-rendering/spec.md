# Spec: keyword-documentation-rendering

## Purpose

Defines how RobotCode renders keyword and library documentation across its surfaces — hover, signature help, completion, the keywords tree view, the Markdown documentation view, the REPL and `robotcode doc` — including argument descriptions, return and raises information, and the normalisation of Markdown-format documentation.

## Requirements

### Requirement: Argument descriptions are rendered with the signature

When a keyword has documented arguments, the rendered keyword documentation SHALL show the argument table with an additional column for the descriptions, so that every argument is named once, with its type, its default value and its description.
- An argument without a description SHALL have an empty description cell.
- A name that the documentation describes without being an argument of the keyword SHALL get a row of its own, with its name and its description and the other cells empty.
- A description SHALL be written into its cell as one line: a line break within a paragraph SHALL become a space, and each further paragraph and each list item SHALL start a new line within the cell (`<br>`). A `|` in a description SHALL be escaped, so that every row has the same number of cells.

A keyword without argument descriptions SHALL keep the argument table without the description column. When a return description exists it SHALL be shown with the return type (`**Return Type**: \`T\` — description`, or `**Returns**: description` without a type); raised exceptions SHALL be listed with their descriptions. Outside the full-page documentation of `library-documentation-markdown`, keywords whose documentation is not in Markdown format and has no argument, return or raises description SHALL render exactly as before, except for the corrections of the requirement "Robot-format tables and links convert to valid Markdown".

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
- **THEN** its hover is identical to the hover before this change, apart from escaped `|` characters in Robot-format table cells and link targets without a `\#` escape

#### Scenario: Markdown library on an older Robot Framework
- **WHEN** a library declares `ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"` and is documented on RF 7.4
- **THEN** its documentation is normalised (reference links, headings, table of contents, admonitions) like on RF 7.5, without argument descriptions

### Requirement: Signature help and completion carry argument descriptions

Signature help SHALL show, for the active parameter, its description followed by the documentation of its types. Completion items for named arguments (`name=`) SHALL carry the argument description as their documentation.

#### Scenario: Signature help for a documented argument
- **WHEN** signature help is requested with the cursor on the `level` argument of `Log` on RF 7.5
- **THEN** the parameter documentation starts with "The log level to use."
- **AND** it contains the documentation of the argument's type

#### Scenario: Named-argument completion
- **WHEN** `level=` is offered as a named-argument completion for `Log` on RF 7.5 and the item is resolved
- **THEN** its documentation contains "The log level to use."

### Requirement: Markdown reference links are resolved

In documentation declared as Markdown, reference-style links (`[Name]`, `[Name][]`, `[text][Name]`) whose target is a keyword of the same library, a type used by the library, a section of the library introduction or one of Libdoc's default targets (introduction, importing, keywords) SHALL NOT be rendered as literal brackets. In hover, signature help and completion, in the output of `robotcode doc keywords` and `robotcode doc keyword`, and in the `doc` and `short_doc` fields of the JSON output of `robotcode doc` they SHALL be rendered as inline code. In full-document views (REPL `.doc`, `robotcode doc lib` and `browse`, Markdown documentation view) they SHALL be rendered as in-document links, where a reference to a type links to the type's heading in the `Data types` section, by the requirement "Data types" of `library-documentation-markdown`. In the REPL keyword view they SHALL be rendered as navigable keyword links. Reference definitions declared in the library introduction SHALL be applied to keyword documentation. Links inside code spans and fenced code blocks, images and unknown targets SHALL be left unchanged. Matching SHALL ignore case and spaces, as Libdoc does.

#### Scenario: Keyword reference in a hover
- **WHEN** the hover for `Log` is shown on RF 7.5
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

### Requirement: Markdown library introductions are normalised

For libraries documented in Markdown, a `%TOC%` line in the introduction SHALL be replaced by a two-level table of contents of the introduction's headings; ATX headings SHALL be shifted one level down (`#` → `##`) as Robot-format headings are today; GitHub-style admonitions (`> [!NOTE]`, `> [!WARNING]`, …) SHALL be rendered as block quotes with a bold label; fenced code, tables and raw HTML SHALL be left unchanged. The backtick auto-linking applied to Robot-format documentation SHALL NOT be applied to Markdown documentation.

#### Scenario: BuiltIn library hover on RF 7.5
- **WHEN** the hover for the `BuiltIn` library import is shown on RF 7.5
- **THEN** it contains no literal `%TOC%`, no line starting with a single `# `, and a table of contents listing the introduction sections

#### Scenario: Admonition in a keyword documentation
- **WHEN** a Collections keyword documentation contains `> [!WARNING]` on RF 7.5
- **THEN** the hover shows a block quote starting with **Warning** and no literal `[!WARNING]`

### Requirement: Robot-format tables and links convert to valid Markdown

When documentation in Robot Framework's format is converted to Markdown, on every surface and every supported Robot Framework version, a `|` inside the content of a table cell SHALL be escaped, so that every table row keeps the number of cells Robot Framework gives it. No link target SHALL contain the escaped `\#`: links converted from Robot-format links and URLs, and the links from backtick names to headings of the same documentation, SHALL be written with `#`. Link texts and all other text SHALL be converted as before, apart from the names in single backticks that the full page links (requirement "Names in Robot-format documentation" of `library-documentation-markdown`).

#### Scenario: Pipe inside a table cell
- **WHEN** the hover for `Should Match Regexp` (BuiltIn) is shown on RF 6.1
- **THEN** the example table row containing `(Foo|Bar)` has as many cells as the header row of its table

#### Scenario: Link with a fragment
- **WHEN** a Robot-format keyword documentation contains `[http://example.com/x.html#frag|docs]`
- **THEN** the rendered documentation contains the link `[docs](http://example.com/x.html#frag)`

#### Scenario: Library introduction on an older Robot Framework
- **WHEN** the hover for a `BuiltIn` import is shown on RF 6.1
- **THEN** it contains the links `[eval](http://docs.python.org/library/functions.html#eval)` and `[str](#str)`
- **AND** no link target contains `\#`

### Requirement: Library scope as Libdoc names it

Library documentation SHALL show the scope of a library as Robot Framework's Libdoc names it: `GLOBAL`, `SUITE` or `TEST`, on every supported Robot Framework version.

#### Scenario: Library hover on Robot Framework 7
- **WHEN** the hover for a `Collections` import is shown on RF 7.5
- **THEN** it shows the scope `GLOBAL`, not `Scope.GLOBAL`

### Requirement: Links to headings use GitHub anchors

Links to headings within library documentation, such as the table of contents that replaces `%TOC%` and the links from backtick names to headings, SHALL point to the anchor that GitHub gives the heading, by the rule of the requirement "Anchors" of `library-documentation-markdown`.

#### Scenario: Library hover with a table of contents
- **WHEN** the hover for a `DateTime` import is shown on RF 7.5
- **THEN** its table of contents links `` `TODAY` and `NOW` `` to `#today-and-now`
