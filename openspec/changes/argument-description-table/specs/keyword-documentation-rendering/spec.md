# Spec Delta

## MODIFIED Requirements

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
