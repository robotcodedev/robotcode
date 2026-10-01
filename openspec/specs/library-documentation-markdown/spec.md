# Spec: library-documentation-markdown

## Purpose

Defines the full-page Markdown documentation of a library, resource file or suite file: its structure and heading hierarchy, keyword order, private keywords, keyword index, data types and the links to them, links from names in Robot-format documentation, anchors and variables in text. It also defines where the page is shown, so that `robotcode doc`, the REPL's `.doc` and editor integrations show one valid, reproducible page on every supported Robot Framework version.

## Requirements

### Requirement: Page structure

The full-page documentation of a library, resource file or suite file SHALL consist of, in this order:

- a level-1 title with the type and the name (`Library *Collections*`);
- the version, when one is set, and the scope;
- a level-2 `Introduction` with the library or resource documentation, when there is any;
- a level-2 `Importing` with the initializer, when it takes arguments;
- a level-2 `Keywords`, when there are keywords;
- a level-2 `Data types`, when the keywords use documented types.

Every keyword and every data type SHALL have a level-3 heading, with the parts of its entry (`Arguments:`, `Documentation:`, and the parts of a data type) as level-4 headings. Markdown headings inside the introduction SHALL start at level 3, one level below the level that the requirement "Markdown library introductions are normalised" of `keyword-documentation-rendering` gives them in other views. Markdown headings inside the documentation of a keyword or of a data type SHALL start at level 5. No Markdown heading SHALL be deeper than level 6. These levels do not apply to documentation in HTML or reStructuredText format, which keeps its HTML headings. Every `---` separator SHALL be preceded by a blank line, so that it never turns the text before it into a heading.

#### Scenario: Markdown-documented standard library
- **WHEN** the page of `Collections` is rendered on RF 7.5
- **THEN** its only level-1 heading is `Library *Collections*`
- **AND** its level-2 headings are exactly `Introduction`, `Keywords` and `Data types`, in this order
- **AND** `Related keywords in BuiltIn` is a level-3 heading inside `Introduction`, and every keyword is a level-3 heading inside `Keywords`

#### Scenario: Robot-format standard library
- **WHEN** the page of `Collections` is rendered on RF 6.1
- **THEN** `Related keywords in BuiltIn` is a level-3 heading inside `Introduction`
- **AND** every keyword is a level-3 heading inside `Keywords`, and the parts of its entry are level-4 headings

#### Scenario: No separator turns text into a heading
- **WHEN** the page of `BuiltIn` is rendered on RF 7.5
- **THEN** no `---` line directly follows a line of text

#### Scenario: Library with initializer arguments
- **WHEN** the page of a library class whose `__init__(self, mode="a")` has a docstring is rendered
- **THEN** a level-2 `Importing` between `Introduction` and `Keywords` shows the argument `mode` with its default `a` and the initializer's documentation
- **AND** the initializer is not shown before the title

#### Scenario: Heading in the documentation of a data type
- **WHEN** the page of a library is rendered on RF 6.1 or newer whose keywords use the types `Alpha` and `Beta`, and the documentation of `Alpha` has the heading `= Usage =`
- **THEN** `Usage` is a level-5 heading, `Data types` is still the last level-2 heading, and both types have their level-3 heading in it

#### Scenario: Resource file
- **WHEN** the page of a `.resource` file with a `Documentation` setting and keywords is rendered
- **THEN** its title is `Resource *<name>*` and it has the level-2 sections `Introduction` and `Keywords` only

### Requirement: Keyword order, private keywords and reproducible output

Keywords SHALL be ordered by name, compared case-insensitively, as Libdoc orders them. Data types SHALL be ordered by name the same way. Keywords tagged `robot:private` SHALL be left out, as in Libdoc's HTML output. Rendering the same documentation twice SHALL produce identical text, whatever the Python hash seed.

#### Scenario: Standard library order
- **WHEN** the page of `Collections` is rendered
- **THEN** its first three keyword headings are `Append To List`, `Combine Lists` and `Convert To Dictionary`

#### Scenario: Resource keywords
- **WHEN** a resource file defines `Zeta Kw` before `Alpha Kw`
- **THEN** its page documents `Alpha Kw` before `Zeta Kw`

#### Scenario: Different hash seeds
- **WHEN** the page of `Collections` is rendered in two processes with different `PYTHONHASHSEED` values
- **THEN** both texts are identical

#### Scenario: Private keyword
- **WHEN** a resource file with a keyword tagged `robot:private` is rendered on RF 6.0 or newer
- **THEN** that keyword appears neither as a heading nor in the keyword index

### Requirement: Keyword index

The `Keywords` section SHALL start with an index: a list with one link per keyword, in the order of the keyword entries, each pointing to the heading of its keyword and showing its name, also when the name contains characters such as `[` and `]`.

#### Scenario: Index of a library
- **WHEN** the page of `Collections` is rendered
- **THEN** the first item after the `Keywords` heading is a link `Append To List` to the anchor of the `Append To List` heading
- **AND** the index has as many links as the section has keyword headings

### Requirement: Data types

With Robot Framework 6.1 or newer, the `Data types` section SHALL document every type that Libdoc documents for the library's keywords, each with its kind and documentation, the allowed values of an enumeration and the structure of a typed dictionary. A table of contents that replaces `%TOC%` SHALL list `Data types` after `Keywords` when the page has the section. In the introduction and in the documentation of keywords, including the descriptions of arguments, return values and exceptions, a reference to a documented type, as a Markdown reference link such as `[Color]` or as a name in single backticks such as `` `Color` `` in Robot Framework's format, SHALL link to the anchor that the requirement "Anchors" gives the type's heading, also when that anchor is numbered. Argument names, the argument and return types of the `Arguments:` parts, and code in double backticks in Robot Framework's format SHALL stay inline code, also when they equal the name of a type.

#### Scenario: Enumeration
- **WHEN** the page of a library with the keyword `paint(self, shade: Color)` and an `Enum` `Color` is rendered on RF 6.1 or newer
- **THEN** `Data types` has a level-3 heading for `Color` that names the kind `Enum` and lists the members of `Color`

#### Scenario: Table of contents
- **WHEN** the page of `BuiltIn` is rendered on RF 7.5
- **THEN** its table of contents lists `Data types` after `Keywords`

#### Scenario: Type reference
- **WHEN** the page of a library with the keyword `paint(self, shade: Color)` and an `Enum` `Color` is rendered on RF 6.1 or newer, and the documentation of `paint` refers to `Color` as `[Color]` in Markdown or as `` `Color` `` in Robot Framework's format
- **THEN** the reference is the link `[Color](#color-enum)` to the heading `Color (Enum)`

#### Scenario: Argument and code named like a type
- **WHEN** the keyword of the scenario "Type reference" also has the argument `color: str`, and its Robot-format documentation also writes the code ``` ``color`` ```
- **THEN** the reference to `Color` is the only link to `#color-enum`
- **AND** the argument name `color`, the argument type `Color` and the code `color` are inline code

#### Scenario: Type heading with a repeated anchor
- **WHEN** the library of the scenario "Type reference" is documented in Markdown and also has the keyword `Color Enum`
- **THEN** the heading of `Color Enum` has the anchor `color-enum` and the heading `Color (Enum)` the anchor `color-enum-1`
- **AND** `[Color]` links to `#color-enum-1`

### Requirement: Names in Robot-format documentation

In documentation in Robot Framework's format, a name in single backticks SHALL link to the heading it names, as Libdoc's HTML links it, also when the name wraps across two lines of a paragraph and whatever text comes before it on the line. The link SHALL point to the heading whose title is the name, also when another heading has the same anchor text. This applies in the introduction and in the documentation of keywords, including the descriptions of arguments, return values and exceptions. The name can be a keyword, a section of the introduction, one of the default sections (introduction, importing, keywords) or a data type; data types are linked by the requirement "Data types". Names in headings and in preformatted text SHALL stay as they are. Argument names, the argument and return types of the `Arguments:` parts, and code in double backticks SHALL stay inline code, also when they equal the name of a keyword or a section, as they do for data types.

#### Scenario: Keyword and section names
- **WHEN** the page of a library documented in Robot Framework's format is rendered, whose introduction has the section `= Section =` and whose keyword `Zeta Kw` is documented with `` `Alpha Kw` `` and `` `Section` ``
- **THEN** these names are the links `[Alpha Kw](#alpha-kw)` and `[Section](#section)`

#### Scenario: Brackets before a name
- **WHEN** the page of `BuiltIn` is rendered on RF 6.1, whose `Remove Tags` documentation writes ``` ``[chars]`` ``` before `` `Glob patterns` ``
- **THEN** `[chars]` is inline code and `Glob patterns` is the link `[Glob patterns](#glob-patterns)`

#### Scenario: Name across two lines
- **WHEN** the page of `BuiltIn` is rendered on RF 6.1, whose `Set Test Variable` documentation writes `` `Set`` at the end of a line and ``Task Variable` `` at the start of the next
- **THEN** it links `Set Task Variable` to `#set-task-variable`

#### Scenario: Names with the same anchor text
- **WHEN** a library has the keywords `Get Value` and `Get-Value` and its documentation names `` `Get-Value` ``
- **THEN** the name links to `#get-value-1`, the heading of `Get-Value`

#### Scenario: Arguments and code named like sections
- **WHEN** the page of `XML` is rendered on RF 6.1 or 7.4, whose introduction has sections named `text`, `tail` and `tag`
- **THEN** the argument names `text`, `tail` and `tag`, and the code ``` ``text`` ``` and ``` ``tail`` ``` in its documentation, are inline code
- **AND** `` `introduction` `` in its documentation links to `#introduction`

### Requirement: Anchors

Every heading of the page SHALL have the anchor GitHub gives it, following github-slugger's rule applied to the text the heading shows: lower case; characters other than letters, marks, digits, `_`, `-` and spaces removed; each space replaced by `-`; a repeated anchor numbered `-1`, `-2`, … in document order. Every link within the page, whose target starts with `#`, SHALL point to the anchor of one of its headings, and no link target SHALL contain `\#`.

#### Scenario: Section title with code
- **WHEN** the page of `DateTime` is rendered on RF 7.5
- **THEN** its table of contents links the section `` `TODAY` and `NOW` `` to `#today-and-now`

#### Scenario: All links resolve
- **WHEN** the pages of `BuiltIn` and of `Collections` are rendered on RF 6.1 and on RF 7.5
- **THEN** the target of every link that starts with `#` equals the anchor of a heading of the same page

#### Scenario: Keyword with embedded arguments
- **WHEN** the page of a resource with the keyword `Open ${browser} Browser` is rendered
- **THEN** the anchor of its heading is `open-browser-browser`

#### Scenario: Heading with emphasis and a link
- **WHEN** a page has the heading `Kw *star* _under_` or `See [the docs](http://example.com) now`
- **THEN** its anchor is `kw-star-under` or `see-the-docs-now`

#### Scenario: Repeated heading text
- **WHEN** a page has two headings with the same text
- **THEN** the first gets the plain anchor and the second the anchor with `-1`

### Requirement: Variables in text are inline code

In the page of a library, resource file or suite file documented in Robot Framework's format, in Markdown or as plain text, every scalar variable in text, such as `${name}` or `${name}[0]`, SHALL be written as inline code, so that Markdown renderers with math support do not show `${x} and ${y}` as a formula. Variables that follow each other directly SHALL form one code span. Code spans, code blocks, HTML blocks and link targets SHALL stay as they are.

#### Scenario: Two variables in a sentence
- **WHEN** the documentation of a resource keyword reads `Use ${x} and ${y}.`
- **THEN** the page contains ``Use `${x}` and `${y}`.``

#### Scenario: Variable in a keyword name
- **WHEN** the page of a resource with the keyword `Set ${a} To ${b}` is rendered
- **THEN** its heading and its index entry show both variables as inline code

#### Scenario: Variables side by side
- **WHEN** the page of `OperatingSystem` is rendered on RF 6.1, whose `Remove Files` example writes `${TEMPDIR}${/}foo.txt`
- **THEN** the page contains ``` `${TEMPDIR}${/}`foo.txt ```

#### Scenario: Variable in code
- **WHEN** a Robot-format documentation writes `${x}` as code (between double backticks) and again inside a preformatted block
- **THEN** the page shows it once as a code span and once inside a code block, without further code marks

### Requirement: Where the page is shown

The REPL's `.doc` command, also at a `robot-debug` stop, and `robotcode doc lib` SHALL show this page.

#### Scenario: REPL
- **WHEN** `.doc Collections` runs in a REPL session that imported `Collections`
- **THEN** the documentation shown has the level-1 heading `Library *Collections*` and the keyword index at the start of `Keywords`
