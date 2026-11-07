# Spec: keyword-documentation-rendering

## Purpose

Defines how RobotCode renders keyword and library documentation across its surfaces — hover, signature help, completion, the keywords tree view, the Markdown documentation view, the REPL and `robotcode doc` — including argument descriptions, return and raises information, and the normalisation of Markdown-format documentation.

## Requirements

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
- **THEN** its hover is identical to the hover before this change, apart from escaped `|` characters in Robot-format table cells, link targets without a `\#` escape, code and plain text in Robot-format documentation, and in VS Code the links to the Documentation Viewer

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

### Requirement: Library scope as Libdoc names it

Library documentation SHALL show the scope of a library as Robot Framework's Libdoc names it: `GLOBAL`, `SUITE` or `TEST`, on every supported Robot Framework version.

#### Scenario: Library hover on Robot Framework 7
- **WHEN** the hover for a `Collections` import is shown on RF 7.5
- **THEN** it shows the scope `GLOBAL`, not `Scope.GLOBAL`

### Requirement: Links to headings use GitHub anchors

Links to headings within library documentation, such as the table of contents that replaces `%TOC%` and the links from backtick names to headings, SHALL point to the anchor that GitHub gives the heading, by the rule of the requirement "Anchors" of `library-documentation-markdown`. In VS Code, such a link carries that anchor to the Documentation Viewer instead, by the requirement "Links in documentation open the Documentation Viewer" of `vscode-documentation-viewer`.

#### Scenario: Library hover with a table of contents
- **WHEN** the hover for a `DateTime` import is shown on RF 7.5 in a language client other than the VS Code extension
- **THEN** its table of contents links `` `TODAY` and `NOW` `` to `#today-and-now`

### Requirement: Description cells of the argument table

A description SHALL be written into its cell as one line: a line break within a paragraph SHALL become a space, and each further paragraph and each list item SHALL start a new line within the cell (`<br>`). A `|` in a description SHALL be escaped, so that every row has the same number of cells. A keyword without argument descriptions SHALL keep the argument table without the description column.

#### Scenario: Line break within a paragraph
- **WHEN** a keyword documents an argument with the paragraph "The first line" followed by the line "of the description"
- **THEN** its description cell shows "The first line of the description" on one line

### Requirement: Return and raises descriptions

When a return description exists it SHALL be shown with the return type (`**Return Type**: \`T\` — description`, or `**Returns**: description` without a type; on the console, `robotcode doc` writes `**Return Type**: \`T\` - description`); on the full page, the names in `T` link to their data types by the requirement "Data types" of `library-documentation-markdown`. Raised exceptions SHALL be listed with their descriptions.

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

Link texts and all other text SHALL be converted as before, apart from the names in single backticks that the full page links (requirement "Names in Robot-format documentation" of `library-documentation-markdown`), code and plain text, by their own requirements, and, in VS Code, the links of the requirement "Links in documentation open the Documentation Viewer" of `vscode-documentation-viewer`, which replace these links there.

#### Scenario: Link text
- **WHEN** a Robot-format keyword documentation contains `[http://example.com|example]`
- **THEN** the rendered documentation contains the link `[example](http://example.com)`

### Requirement: Code keeps the text of the documentation

When documentation in Robot Framework's format is converted to Markdown, on every surface and every supported Robot Framework version, code SHALL keep the text as written, so that a reader can copy it and paste it without rework. Code is text in double backticks, whatever else Markdown reads as a code span, and preformatted blocks. Nothing in code SHALL be escaped or become bold, italic, a link or an image.

#### Scenario: Characters that plain text escapes
- **WHEN** a Robot-format documentation writes ``` ``vscode/<n>`` ``` and ``` ``#FF00FF`` ```
- **THEN** the rendered documentation contains `` `vscode/<n>` `` and `` `#FF00FF` ``

#### Scenario: The same characters in plain text
- **WHEN** a Robot-format documentation writes `a < b` and `issue #42` outside of code
- **THEN** the rendered documentation contains `a \< b` and `issue \#42`

#### Scenario: Bold and italic markers in code
- **WHEN** a Robot-format documentation writes ``` ``a *b* c`` ``` and ``` ``a _b_ c`` ```
- **THEN** the rendered documentation contains `` `a *b* c` `` and `` `a _b_ c` ``

#### Scenario: URL in code
- **WHEN** a Robot-format documentation writes ``` ``see http://example.com/x now`` ```
- **THEN** the rendered documentation contains `` `see http://example.com/x now` ``

#### Scenario: Bold around code
- **WHEN** a Robot-format documentation writes ``` *bold ``<a>`` bold* ```
- **THEN** the rendered documentation contains `` **bold `<a>` bold** ``

#### Scenario: Name without a link target
- **WHEN** a Robot-format documentation writes `` `<x>` `` and nothing can be linked to that name
- **THEN** the rendered documentation contains `` `<x>` ``

#### Scenario: Double backticks that Robot Framework does not read as code
- **WHEN** a Robot-format documentation writes ``` ``<a>``s ```
- **THEN** the rendered documentation contains ``` ``<a>``s ```

#### Scenario: Backtick in code
- **WHEN** a Robot-format documentation writes ``` ``a`b`` ```
- **THEN** the rendered documentation shows one code span with the text ``a`b``

#### Scenario: Backtick without a partner before code
- **WHEN** a Robot-format documentation writes ``` don`t use ``<a>`` here ```
- **THEN** the rendered documentation shows a literal backtick in ``don`t`` and `<a>` as code

#### Scenario: Double backticks without a partner before code
- **WHEN** a Robot-format documentation writes ``` Use `` in ``a``. ```
- **THEN** the rendered documentation shows two literal backticks after `Use` and `a` as code

#### Scenario: Backtick after a backslash
- **WHEN** a Robot-format documentation writes `` \`<b>` is escaped ``
- **THEN** the rendered documentation shows `<b>` as text and no code span

#### Scenario: Code at the start of a paragraph
- **WHEN** a Robot-format documentation has a paragraph that starts with ``` ``True``/``False`` enable it. ``` and a heading after it
- **THEN** the paragraph holds one code span and the heading stays a heading

#### Scenario: Private-use characters in the documentation
- **WHEN** a Robot-format documentation writes the characters U+E000, `5` and U+E001 and then ``` ``x`` ```
- **THEN** the rendered documentation shows these characters and `x` as code

#### Scenario: Section header in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line `| *** Test Cases ***`
- **THEN** the code block in the rendered documentation contains `*** Test Cases ***`

### Requirement: Markup of links and names falls away in code

In code, the markup of links and names, which Libdoc does not show either, SHALL fall away and its text SHALL stay: a link `[target|text]` becomes `text`, and a name in single backticks inside code becomes the name. Text around the markup SHALL stay as written.

#### Scenario: Name in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line ``| `Add Cookie`   foo   bar``
- **THEN** the code block in the rendered documentation contains `Add Cookie   foo   bar`

#### Scenario: Link in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line `| [https://example.com/x|response] => 1`
- **THEN** the code block in the rendered documentation contains `response => 1`

#### Scenario: Text around a link in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line `| a | b [x|y] c | d`
- **THEN** the code block in the rendered documentation contains `a | b y c | d`

#### Scenario: Name in a code span
- **WHEN** a Robot-format documentation writes ``` ``x `Alpha Kw` y`` ``` and the library has the keyword `Alpha Kw`
- **THEN** the rendered documentation contains `` `x Alpha Kw y` `` without a link

#### Scenario: Link in a code span
- **WHEN** a Robot-format documentation writes ``` ``see [a|b] now`` ```
- **THEN** the rendered documentation contains `` `see b now` ``

#### Scenario: Link without text in code
- **WHEN** a Robot-format documentation writes ``` ``[,|]`` ``` or has the preformatted line `| Use [,|].`
- **THEN** the rendered documentation contains `` `,` `` or `Use ,.`

### Requirement: Backticks in preformatted blocks

In a preformatted block, code in double backticks SHALL lose its backticks, because the whole block already is code. Three backticks in a row SHALL become one, as Libdoc shows them, because the format has no way to escape a backtick.

#### Scenario: Code in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line ``| Get Text    h1    # Returns ``${True}`` ``
- **THEN** the code block in the rendered documentation contains `Get Text    h1    # Returns ${True}`

#### Scenario: Three backticks in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line ``| const s = ```Hello ${name}```; ``
- **THEN** the code block in the rendered documentation contains ``const s = `Hello ${name}`;``

#### Scenario: One backtick in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line ``| a ` b``
- **THEN** the code block in the rendered documentation contains ``a ` b``

#### Scenario: Line of backticks in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted lines `| first`, ``| ```` `` and `| second`
- **THEN** all three lines stay in one code block

### Requirement: Plain text keeps its characters

When documentation in Robot Framework's format is converted to Markdown, on every surface and every supported Robot Framework version, text that Robot Framework does not read as markup SHALL show the same characters as in Libdoc, in paragraphs, list items and table cells. Bold, italic, links and images as Robot Framework reads them SHALL stay.

#### Scenario: Backslashes
- **WHEN** a Robot-format documentation writes `\\d+` and `C:\\temp` in plain text or in a table cell
- **THEN** the reader sees `\\d+` and `C:\\temp`

#### Scenario: Escaped variable
- **WHEN** a Robot-format documentation writes `\${name}`
- **THEN** the reader sees `\${name}`, and it is not inline code on a documentation page

#### Scenario: Stars Robot Framework does not read as bold
- **WHEN** a Robot-format documentation writes `*HTML*Test`, `.*foo.*` and `2*3*4`
- **THEN** the reader sees them as written

#### Scenario: Underscores Robot Framework does not read as italic
- **WHEN** a Robot-format documentation writes `__init__` and `_private`
- **THEN** the reader sees them as written

#### Scenario: Entities
- **WHEN** a Robot-format documentation writes `a &lt; b`
- **THEN** the reader sees `a &lt; b`

#### Scenario: Markdown link syntax
- **WHEN** a Robot-format documentation writes `[text](http://example.com/x)`
- **THEN** the reader sees it as written

#### Scenario: Strikethrough syntax
- **WHEN** a Robot-format documentation writes `~~text~~`
- **THEN** the reader sees it as written

#### Scenario: Paragraphs that start like a Markdown block
- **WHEN** a paragraph of a Robot-format documentation starts with `> `, `+ `, `* `, `1. `, `1) ` or `[x]: `, or consists of `-`
- **THEN** the reader sees that text as written, in a paragraph

#### Scenario: Robot Framework's markup stays
- **WHEN** a Robot-format documentation writes `*bold*`, `_italic_`, `[http://example.com/x|the docs]` and `http://example.com/a_b#c`
- **THEN** the reader sees bold and italic text and two links, the second with the text `http://example.com/a_b#c`

#### Scenario: Backslashes only where Markdown needs them
- **WHEN** a Robot-format documentation writes `snake_case_name`, `${list}[0]`, `2 * 3`, `R&D` and `C:\temp`
- **THEN** the Markdown contains them without an added backslash

#### Scenario: Less-than sign in a heading
- **WHEN** a Robot-format documentation has the heading `= Section <b> here =`, or a library has a keyword named `Run <x> Now`
- **THEN** the reader sees `Section <b> here` and `Run <x> Now`, and links to them find their headings

#### Scenario: Name of a test in the hover
- **WHEN** the hover for a test named `Run *this* <now>` is shown
- **THEN** its heading shows `Test Case` and the name as written, in italics

#### Scenario: Only Markdown comes out
- **WHEN** a Robot-format documentation with bold, italic, code, links, tables and preformatted blocks is converted
- **THEN** the result is plain Markdown, with no HTML and no characters that only the conversion uses

#### Scenario: Variable with special characters on a documentation page
- **WHEN** the documentation of a library written in Robot Framework's format writes `${_x_}` and `${x#y}`
- **THEN** its page contains `` `${_x_}` `` and `` `${x#y}` ``
