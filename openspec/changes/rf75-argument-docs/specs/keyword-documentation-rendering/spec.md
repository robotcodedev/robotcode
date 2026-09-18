# Spec Delta

## Purpose

Defines how RobotCode renders keyword and library documentation across its surfaces — hover, signature help, completion, the keywords tree view, the Markdown documentation view and the REPL — including argument descriptions, return and raises information, and the normalisation of Markdown-format documentation.

## ADDED Requirements

### Requirement: Argument descriptions are rendered with the signature

When a keyword has documented arguments, the rendered keyword documentation SHALL show, after the argument table, one entry per documented argument with its name and description; multi-line descriptions SHALL be preserved. When a return description exists it SHALL be shown with the return type (`**Return Type**: \`T\` — description`, or `**Returns**: description` without a type); raised exceptions SHALL be listed with their descriptions. Keywords whose documentation is not in Markdown format and has no argument, return or raises description SHALL render exactly as before.

#### Scenario: Standard-library keyword on RF 7.5
- **WHEN** the hover for `Log` (BuiltIn) is shown on RF 7.5
- **THEN** the argument table is followed by entries such as `message`: "The message to log." and `level`: "The log level to use."
- **AND** the documentation text below contains no `Args:` block

#### Scenario: Keyword with return and raises documentation
- **WHEN** a keyword documents `Returns:` and `Raises:` sections on RF 7.5
- **THEN** the rendered documentation shows the return description next to the return type and a `Raises` list with each exception and its description

#### Scenario: Keyword without descriptions in a non-Markdown library
- **WHEN** a keyword of a library documented in Robot, reStructuredText, HTML or plain-text format has no Google-style sections, or the installed Robot Framework is older than 7.5
- **THEN** the rendered documentation is identical to the rendering before this change

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

In documentation declared as Markdown, reference-style links (`[Name]`, `[Name][]`, `[text][Name]`) whose target is a keyword of the same library, a type used by the library, a section of the library introduction or one of Libdoc's default targets (introduction, importing, keywords) SHALL NOT be rendered as literal brackets. In hover, signature help and completion they SHALL be rendered as inline code; in full-document views (REPL `.doc`, Markdown documentation view) as in-document links; in the REPL keyword view as navigable keyword links. Reference definitions declared in the library introduction SHALL be applied to keyword documentation. Links inside code spans and fenced code blocks, images and unknown targets SHALL be left unchanged. Matching SHALL ignore case and spaces, as Libdoc does.

#### Scenario: Keyword reference in a hover
- **WHEN** the hover for `Log` is shown on RF 7.5
- **THEN** `[Set Log Level]` is rendered as `` `Set Log Level` `` and `[String representations]` as `` `String representations` ``

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
