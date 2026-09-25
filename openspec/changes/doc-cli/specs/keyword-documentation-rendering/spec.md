# Spec Delta

## MODIFIED Requirements

### Requirement: Argument descriptions are rendered with the signature

When a keyword has documented arguments, the rendered keyword documentation SHALL list every argument once, with its type, its default value and its description, as Robot Framework's Libdoc lists them, instead of showing the argument table and the descriptions separately; multi-line descriptions SHALL be preserved. A keyword without argument descriptions SHALL keep the argument table. When a return description exists it SHALL be shown with the return type (`**Return Type**: \`T\` — description`, or `**Returns**: description` without a type); raised exceptions SHALL be listed with their descriptions. Keywords whose documentation is not in Markdown format and has no argument, return or raises description SHALL render exactly as before, except for the corrections of the requirement "Robot-format tables and links convert to valid Markdown".

#### Scenario: Standard-library keyword on RF 7.5
- **WHEN** the hover for `Log` (BuiltIn) is shown on RF 7.5
- **THEN** the arguments are listed as entries such as `message`: `object` — "The message to log." and `level`: … = `INFO` — "The log level to use.", and no argument is named twice
- **AND** the documentation text below contains no `Args:` block

#### Scenario: Keyword with return and raises documentation
- **WHEN** a keyword documents `Returns:` and `Raises:` sections on RF 7.5
- **THEN** the rendered documentation shows the return description next to the return type and a `Raises` list with each exception and its description

#### Scenario: Keyword without descriptions in a non-Markdown library
- **WHEN** a keyword of a library documented in Robot, reStructuredText, HTML or plain-text format has no Google-style sections, or the installed Robot Framework is older than 7.5
- **THEN** the rendered documentation is identical to the rendering before this change, apart from escaped `|` characters in Robot-format table cells and link targets without a `\#` escape

#### Scenario: Markdown library on an older Robot Framework
- **WHEN** a library declares `ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"` and is documented on RF 7.4
- **THEN** its documentation is normalised (reference links, headings, table of contents, admonitions) like on RF 7.5, without argument descriptions

## ADDED Requirements

### Requirement: Robot-format tables and links convert to valid Markdown

When documentation in Robot Framework's format is converted to Markdown, on every surface and every supported Robot Framework version, a `|` inside the content of a table cell SHALL be escaped so that every table row keeps the number of cells Robot Framework gives it, and the target of a link converted from a Robot-format link or URL SHALL contain `#` instead of the escaped `\#`. Link texts and all other text SHALL be converted as before.

#### Scenario: Pipe inside a table cell
- **WHEN** the hover for `Should Match Regexp` (BuiltIn) is shown on RF 6.1
- **THEN** the example table row containing `(Foo|Bar)` has as many cells as the header row of its table

#### Scenario: Link with a fragment
- **WHEN** a Robot-format keyword documentation contains `[http://example.com/x.html#frag|docs]`
- **THEN** the rendered documentation contains the link `[docs](http://example.com/x.html#frag)`
