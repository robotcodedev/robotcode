# Spec Delta: library-documentation-markdown

## MODIFIED Requirements

### Requirement: Data types

With Robot Framework 6.1 or newer, the `Data types` section SHALL document every type that Libdoc documents for the library's keywords, each with its kind and documentation, the allowed values of an enumeration and the structure of a typed dictionary. A table of contents that replaces `%TOC%` SHALL list `Data types` after `Keywords` when the page has the section. In the introduction and in the documentation of keywords, including the descriptions of arguments, return values and exceptions, a reference to a documented type, as a Markdown reference link such as `[Color]` or as a name in single backticks such as `` `Color` `` in Robot Framework's format, SHALL link to the anchor that the requirement "Anchors" gives the type's heading, also when that anchor is numbered.

In the argument tables of the keywords and of the initializer, and in the return types, each name of a type that Libdoc maps to a documented type, such as `int` to `integer`, SHALL link to the anchor that the requirement "Anchors" gives that type's heading, also when that anchor is numbered, and SHALL stay inline code inside the link. The rest of a type, such as brackets, the values of a `Literal` and the names of types without documentation, SHALL stay inline code, and the members of a union SHALL stay separated by `|`. A type that names no documented type SHALL be written as before, and every row of an argument table SHALL keep its number of cells. Argument names and code in double backticks in Robot Framework's format SHALL stay inline code, also when they equal the name of a type.

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
- **THEN** the argument name `color` and the code `color` are inline code
- **AND** the type of `shade` is the link ``[`Color`](#color-enum)``, and the type `str` of `color` links to the heading `string (Standard)`

#### Scenario: Type heading with a repeated anchor
- **WHEN** the library of the scenario "Type reference" is documented in Markdown and also has the keyword `Color Enum`
- **THEN** the heading of `Color Enum` has the anchor `color-enum` and the heading `Color (Enum)` the anchor `color-enum-1`
- **AND** `[Color]` and the type of `shade` link to `#color-enum-1`

#### Scenario: Types of XML
- **WHEN** the page of `XML` is rendered on RF 7.4 or 7.5
- **THEN** in the argument table of `Parse Xml`, the type `Source` is the link ``[`Source`](#source-custom)`` and `bool` links to `#boolean-standard`
- **AND** its return type is the link ``[`Element`](#element-custom)``

#### Scenario: Nested types, unions and literals
- **WHEN** the page of a library is rendered on RF 7.0 or newer, whose keyword has the arguments `values: list[int]`, `limit: int | None` and `mode: Literal['a', 'b']`
- **THEN** `list`, `int`, `None` and `Literal` link to their headings in `Data types`, the brackets and `'a', 'b'` are inline code, `int` and `None` are separated by `|`
- **AND** every row of the argument table has as many cells as its header

#### Scenario: Type without documentation
- **WHEN** the page of `BuiltIn` is rendered on RF 7.5
- **THEN** the type `Collection` of the argument `container` of `Should Contain` is inline code

### Requirement: Names in Robot-format documentation

In documentation in Robot Framework's format, a name in single backticks SHALL link to the heading it names, as Libdoc's HTML links it, also when the name wraps across two lines of a paragraph and whatever text comes before it on the line. The link SHALL point to the heading whose title is the name, also when another heading has the same anchor text. This applies in the introduction and in the documentation of keywords, including the descriptions of arguments, return values and exceptions. The name can be a keyword, a section of the introduction, one of the default sections (introduction, importing, keywords) or a data type; data types are linked by the requirement "Data types". Names in headings and in preformatted text SHALL stay as they are. Argument names and code in double backticks SHALL stay inline code, also when they equal the name of a keyword, a section or a data type; argument and return types link only to data types, by the requirement "Data types".

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
