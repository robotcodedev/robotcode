# Spec Delta

## ADDED Requirements

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
- **THEN** its hover is identical to the hover before this change, apart from escaped `|` characters in Robot-format table cells, link targets without a `\#` escape, code in Robot-format documentation, and in VS Code the links to the Documentation Viewer

#### Scenario: Markdown library on an older Robot Framework
- **WHEN** a library declares `ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"` and is documented on RF 7.4
- **THEN** its documentation is normalised (reference links, headings, table of contents, admonitions) like on RF 7.5, without argument descriptions

### Requirement: Other Robot-format text converts as before

Link texts and all other text SHALL be converted as before, apart from the names in single backticks that the full page links (requirement "Names in Robot-format documentation" of `library-documentation-markdown`), code (requirements "Code keeps the text of the documentation", "Markup of links and names falls away in code" and "Backticks in preformatted blocks") and, in VS Code, the links of the requirement "Links in documentation open the Documentation Viewer" of `vscode-documentation-viewer`, which replace these links there.

#### Scenario: Link text
- **WHEN** a Robot-format keyword documentation contains `[http://example.com|example]`
- **THEN** the rendered documentation contains the link `[example](http://example.com)`
