# Spec Delta

<!-- The hover part of "Existing documentation surfaces keep their rendering" follows the recommended default of design question Q4. -->

## Purpose

Defines the canonical Markdown form of the documentation of a library or resource file — its structure, keyword and type entries, ordering, the conversion of every documentation format, table of contents, links, anchors, navigation outline and load errors — so that the documentation command, its terminal browser and later editor integrations show and write one identical form on every supported Robot Framework version.

## ADDED Requirements

### Requirement: Canonical document structure

The canonical documentation of a library or resource file SHALL consist of, in this order: one level-1 heading with the library or resource name; a metadata list with the type (library or resource), the version when one is set, the scope for libraries as Libdoc names it (`GLOBAL`, `SUITE` or `TEST`), the source file as a path relative to the project root when the file lies inside the project (otherwise no source entry), and the import arguments when they were given; a level-2 `Introduction` section with the library or resource documentation, when there is any; a level-2 `Importing` section when the library's initializer accepts arguments or the documentation has load errors; a level-2 `Keywords` section with one level-3 heading per keyword, when there are keywords; and a level-2 `Data types` section with one level-3 heading per documented type, when there are any. No other level-1 or level-2 headings SHALL occur. Headings inside documentation texts SHALL be nested below the heading they belong to — headings of the introduction start at level 3, headings inside keyword, initializer and type documentation at level 4 — and deeper levels SHALL be capped at level 6. The parts of a keyword, initializer or type entry (arguments, return value, raised exceptions, tags, allowed values, usages) SHALL NOT be headings.

#### Scenario: Markdown-documented standard library
- **WHEN** the canonical documentation of `Collections` is rendered on RF 7.5
- **THEN** the only level-1 heading is `Collections` and its metadata names the version `7.5` and the scope `GLOBAL`
- **AND** the level-2 headings are exactly `Introduction`, `Keywords` and `Data types`, in this order
- **AND** `Related keywords in BuiltIn`, `Using with list-like and dictionary-like objects` and `Ignore case` are level-3 headings inside `Introduction`
- **AND** every keyword is a level-3 heading inside `Keywords` and no heading reads `Arguments` or `Documentation`

#### Scenario: Robot-format standard library on an older Robot Framework
- **WHEN** the canonical documentation of `Collections` is rendered on RF 6.1
- **THEN** the `= Related keywords in BuiltIn =` section of its introduction is a level-3 heading inside `Introduction`
- **AND** the level-2 headings are exactly `Introduction` and `Keywords`

#### Scenario: Library with initializer arguments
- **WHEN** a library class whose `__init__(self, mode="a")` has a docstring is documented
- **THEN** a level-2 `Importing` section between `Introduction` and `Keywords` shows the argument `mode` with its default `a` and the initializer's documentation, without a heading of its own

#### Scenario: Resource file
- **WHEN** a `.resource` file with a `Documentation` setting and two keywords inside the project is documented
- **THEN** the document starts with its name as level-1 heading and a metadata list with the type resource, no scope and the source path relative to the project root
- **AND** it has the level-2 sections `Introduction` and `Keywords` and neither `Importing` nor `Data types`

### Requirement: Keyword entries

Each keyword entry SHALL show, in this order: every argument exactly once with its kind (variable positional, variable named, named-only, positional-only), its types, its default value and its description; the return type together with the return description; the raised exceptions with their descriptions; the tags; and the documentation text. The initializer in `Importing` SHALL be shown the same way without a heading. An argument or return type that has an entry in `Data types` SHALL link to that entry. A type entry SHALL show the kind of type, its documentation, the allowed values of an enumeration, the structure of a typed dictionary, the accepted value types and links to the keywords that use it.

#### Scenario: Keyword with argument descriptions
- **WHEN** the canonical documentation of `BuiltIn` is rendered on RF 7.5
- **THEN** the `Log` entry lists `message` with "The message to log." and `level` with its default `INFO` and "The log level to use.", each argument once
- **AND** the documentation text of the entry contains no `Args:` block

#### Scenario: Keyword without argument descriptions
- **WHEN** the canonical documentation of `BuiltIn` is rendered on RF 6.1
- **THEN** the `Should Be Equal` entry lists `first`, `second`, `msg` and its other arguments once each, with their default values, and no Markdown table of arguments

#### Scenario: Link from an argument type to its data type
- **WHEN** a library keyword `paint(self, shade: Color)` with an `Enum` `Color` is documented on RF 6.1 or newer
- **THEN** the `shade` argument links `Color` to the `Color` entry under `Data types`
- **AND** that entry names the kind `Enum`, lists the members of `Color` and links to `Paint`

### Requirement: Order, private keywords and reproducible output

Keywords SHALL be ordered as Robot Framework's Libdoc orders them, by name compared case-insensitively; data types SHALL be ordered by name the same way. Keywords tagged `robot:private` SHALL be left out, as in Libdoc's HTML output. Rendering the same documentation twice SHALL produce identical text, independent of the Python hash seed.

#### Scenario: Standard library order
- **WHEN** the canonical documentation of `Collections` is rendered on RF 7.5
- **THEN** the first three keyword headings are `Append To List`, `Combine Lists` and `Convert To Dictionary`

#### Scenario: Resource keywords in definition order
- **WHEN** a resource file defines `Zeta Kw` before `Alpha Kw`
- **THEN** `Alpha Kw` is documented before `Zeta Kw`

#### Scenario: Different hash seeds
- **WHEN** the canonical documentation of `Collections` is rendered in two processes with different `PYTHONHASHSEED` values
- **THEN** both texts are identical

#### Scenario: Private keyword
- **WHEN** a resource file has a keyword tagged `robot:private` and is documented on RF 6.0 or newer
- **THEN** that keyword appears neither as a heading nor in the navigation outline

### Requirement: One Markdown form for every documentation format

Documentation SHALL be converted to Markdown by the same rules on every supported Robot Framework version: Robot Framework's documentation format by RobotCode's Robot-to-Markdown conversion, Markdown documentation with the normalisation RobotCode applies in the editors (admonitions, reference links), reStructuredText and HTML documentation as the editors show them, plain text as written apart from the links below. A `%TOC%` line in the introduction of Robot-format or Markdown documentation SHALL be replaced by a table of contents of the introduction's sections with their subsections (two levels; a subsection that precedes the first section is not listed, as Robot Framework 7.5's Libdoc builds it for the Robot format), followed by the `Importing`, `Keywords` and `Data types` sections the document has. References to keywords, types and sections of the same document — Markdown reference links (`[Name]`) and backtick names (`` `Name` ``) in Robot-format and plain-text documentation — SHALL link to their headings, matched case- and space-insensitively as Libdoc matches them; an unknown Markdown reference SHALL stay as written and an unknown backtick name SHALL stay inline code. A `|` inside a table cell SHALL be escaped and no link target SHALL contain a `\#` escape.

#### Scenario: Markdown library with a table of contents and references
- **WHEN** the canonical documentation of `BuiltIn` is rendered on RF 7.5
- **THEN** it contains no literal `%TOC%`
- **AND** the table of contents lists the introduction's sections followed by `Keywords` and `Data types`
- **AND** `[Set Log Level]` in the `Log` entry is a link to the `Set Log Level` heading

#### Scenario: Robot-format library on an older Robot Framework
- **WHEN** the canonical documentation of `BuiltIn` is rendered on RF 6.1
- **THEN** `` `Should Be Equal` `` in the introduction is a link to the `Should Be Equal` heading
- **AND** the table of contents starts with `HTML error messages` and has no `Table of contents` entry
- **AND** the example table row of `Should Match Regexp` that contains `(Foo|Bar)` has as many cells as the header row of its table
- **AND** no link target contains `\#`

#### Scenario: Admonition
- **WHEN** the canonical documentation of `Collections` is rendered on RF 7.5
- **THEN** a `> [!WARNING]` block of a keyword is rendered as a block quote starting with **Warning** and no literal `[!WARNING]` remains

### Requirement: Anchors

Every heading SHALL have an anchor derived from its text by one documented rule. Anchors SHALL be unique within a document, every in-document link SHALL point to an existing anchor, and the anchors of keywords and sections SHALL NOT depend on the `Data types` section. The rule SHALL be the same for every document and every supported Robot Framework version.

#### Scenario: All links resolve
- **WHEN** the canonical documentation of `BuiltIn` and of `Collections` is rendered on RF 6.1 and on RF 7.5
- **THEN** the target of every in-document link equals the anchor of exactly one heading of the same document

#### Scenario: Heading text used twice
- **WHEN** a library's introduction has a section named like one of its keywords
- **THEN** the section and the keyword get different anchors
- **AND** navigating to the keyword by its name leads to the keyword's heading, not to the section

### Requirement: Navigation outline

Together with the Markdown, the canonical documentation SHALL provide its outline: one entry per heading in document order with the kind of target (the document, a section, the importing section, a keyword or a type), its name, its heading level and its anchor. Consumers SHALL be able to navigate to a keyword by its name as Robot Framework matches keyword names (case, spaces and underscores ignored), to a type by its name and to a section by its title, without computing anchors themselves.

#### Scenario: Keyword found by its Python name
- **WHEN** the outline of a library with the keyword `Do Thing` is searched for the keyword `do_thing`
- **THEN** the entry for `Do Thing` with its anchor and heading level is found

#### Scenario: Outline order
- **WHEN** the canonical documentation of a library with an introduction section, an initializer with arguments, keywords and a data type is rendered
- **THEN** the outline lists the document, `Introduction`, the introduction section, `Importing`, `Keywords`, the keywords, `Data types` and the type, in this order

### Requirement: Load errors are part of the document

When a library's documentation has load errors, the `Importing` section SHALL be present and SHALL list every error message, with its source and line when known, before the initializer. The document SHALL still contain everything that could be documented.

#### Scenario: Library that cannot be imported
- **WHEN** the documentation of a library name that no module has is rendered
- **THEN** the document has the library name as level-1 heading and an `Importing` section with the import error
- **AND** it has no `Keywords` section

### Requirement: Existing documentation surfaces keep their rendering

Hover, signature help, completion, the keywords tree view and the REPL keyword view (`.kw`) SHALL NOT switch to the canonical form, and their keyword documentation SHALL keep its rendering apart from the Robot-format conversion corrections of `keyword-documentation-rendering`. The canonical form SHALL be used only where a requirement says so.

#### Scenario: Keyword hover
- **WHEN** the hover for `Log` is shown on RF 7.5 and on RF 6.1
- **THEN** it is identical to the hover before this change
