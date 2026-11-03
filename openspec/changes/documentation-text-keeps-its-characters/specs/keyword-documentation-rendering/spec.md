# Spec Delta

## ADDED Requirements

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

#### Scenario: Only Markdown comes out
- **WHEN** a Robot-format documentation with bold, italic, code, links, tables and preformatted blocks is converted
- **THEN** the result is plain Markdown, with no HTML and no characters that only the conversion uses

#### Scenario: Variable with special characters on a documentation page
- **WHEN** the documentation of a library written in Robot Framework's format writes `${_x_}` and `${x#y}`
- **THEN** its page contains `` `${_x_}` `` and `` `${x#y}` ``

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
- **THEN** its hover is identical to the hover before this change, apart from escaped `|` characters in Robot-format table cells, link targets without a `\#` escape, code and plain text in Robot-format documentation, and in VS Code the links to the Documentation Viewer

#### Scenario: Markdown library on an older Robot Framework
- **WHEN** a library declares `ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"` and is documented on RF 7.4
- **THEN** its documentation is normalised (reference links, headings, table of contents, admonitions) like on RF 7.5, without argument descriptions

### Requirement: Other Robot-format text converts as before

Link texts and all other text SHALL be converted as before, apart from the names in single backticks that the full page links (requirement "Names in Robot-format documentation" of `library-documentation-markdown`), code (requirements "Code keeps the text of the documentation", "Markup of links and names falls away in code" and "Backticks in preformatted blocks"), plain text (requirement "Plain text keeps its characters") and, in VS Code, the links of the requirement "Links in documentation open the Documentation Viewer" of `vscode-documentation-viewer`, which replace these links there.

#### Scenario: Link text
- **WHEN** a Robot-format keyword documentation contains `[http://example.com|example]`
- **THEN** the rendered documentation contains the link `[example](http://example.com)`
