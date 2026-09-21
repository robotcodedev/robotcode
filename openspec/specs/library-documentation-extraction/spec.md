# Spec: library-documentation-extraction

## Purpose

Defines what RobotCode extracts from library and resource keyword documentation — tags declared in documentation, privacy, unescaping, documentation formats, standard type documentation, type aliases and return types — and guarantees that the result is the same on every supported Robot Framework version and never alters Robot Framework's own objects.

## Requirements

### Requirement: Tags declared in documentation are extracted

RobotCode SHALL treat tags declared in keyword documentation — the `Tags:` section of a Python keyword docstring and of a resource keyword's `[Documentation]` — as keyword tags, merged with tags declared via `[Tags]` or `robot_tags`. A keyword whose merged tags contain `robot:private` SHALL be private. In resource keywords a documentation tag written as `-name` SHALL remove `name` from the merged tags on Robot Framework ≥ 7.4 (the first version whose Libdoc does so; older versions keep it literally); in library keywords it SHALL be kept literally. A `Tags:` section that is the only Google-style section of the documentation, or that is the trailing line of the documentation, SHALL NOT appear in the rendered documentation text; a documentation that also contains `Args:`, `Returns:` or `Raises:` sections is otherwise rendered unchanged (see "Documentation content is never dropped"). Tags and privacy SHALL be the ones Robot Framework's own Libdoc reports for the installed version, identical on RF 7.4 and RF 7.5, and the documentation text SHALL be identical whenever the `Tags:` section is in a form Robot Framework 7.4 recognised (a trailing `Tags:` line).

#### Scenario: Library keyword docstring with a Tags section
- **WHEN** a Python keyword's docstring ends with `Tags: alpha, beta` and the library is documented on RF 7.4 and on RF 7.5
- **THEN** the keyword's tags contain `alpha` and `beta` on both versions
- **AND** the rendered documentation contains no `Tags:` line on either version

#### Scenario: Private keyword declared through documentation
- **WHEN** a Python keyword's docstring ends with `Tags: robot:private`
- **THEN** the keyword is private (hover marks it as private, and it is deprioritised when a non-private keyword with the same name exists)

#### Scenario: Negated documentation tag in a resource keyword
- **WHEN** a resource keyword has `[Tags]    keep    stay` and a `[Documentation]` ending with `Tags: -keep, other` and is documented on RF 7.4 and on RF 7.5
- **THEN** the keyword's tags are `other` and `stay` on both versions

### Requirement: Resource keyword documentation is unescaped

RobotCode SHALL remove Robot Framework backslash escapes from resource keyword and resource file documentation before rendering it, on every supported Robot Framework version.

#### Scenario: Escaped markup in a resource keyword documentation
- **WHEN** a resource keyword's `[Documentation]` contains `\*not bold\*`
- **THEN** the rendered documentation text contains `*not bold*` on RF 7.4 and on RF 7.5

### Requirement: Documentation content is never dropped

When RobotCode does not render a part of a keyword's documentation separately, that part SHALL remain in the documentation text. In particular Google-style `Args:`, `Returns:` and `Raises:` sections SHALL stay in the documentation text as long as RobotCode has no dedicated rendering for them.

#### Scenario: Google-style docstring on RF 7.5
- **WHEN** `BuiltIn.Log` is documented on RF 7.5
- **THEN** the argument descriptions of its `Args:` section are present in the hover text

### Requirement: Documentation extraction does not mutate Robot Framework objects

Rendering documentation for a library or resource that is already loaded by a running Robot Framework session (for example the REPL's `.doc` command) SHALL leave the session's keyword objects unchanged: their documentation strings and tags SHALL be identical before and after rendering.

#### Scenario: REPL documentation of an imported library
- **WHEN** a REPL session imports a library whose keyword docstring ends with `Tags: alpha` and then renders that keyword's documentation
- **THEN** the rendered documentation lists the tag `alpha`
- **AND** the running keyword object's `doc` and `tags` are unchanged

### Requirement: Standard type documentation follows the library's documentation format

Documentation of standard argument types (`integer`, `boolean`, `string`, …) SHALL be produced in the documentation format the library declares, so that it renders correctly together with the library's own documentation. Markdown-documented libraries SHALL NOT show Robot Framework link markup in type documentation.

#### Scenario: Type documentation of a Markdown library
- **WHEN** the `integer` type documentation of `BuiltIn` is rendered on RF 7.5
- **THEN** the rendered text contains no `[https://…|int]` Robot link markup

#### Scenario: Type documentation of a Robot-format library
- **WHEN** the `integer` type documentation of a library with `ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"` is rendered
- **THEN** it is converted from Robot Framework's documentation format to Markdown as before

### Requirement: Type aliases do not break type documentation

Libraries whose keywords use Python `type` statement aliases SHALL be documented completely. A recursive alias (`type Tree = int | list[Tree]`) SHALL NOT cause an error and SHALL NOT remove the type documentation of the library's other types; the alias name SHALL be shown as the argument type.

#### Scenario: Recursive alias in a library
- **WHEN** a library defines `type ID = int`, `type Tree = int | list[Tree]` and keywords with arguments `id: ID` and `tree: Tree`, and is documented on RF 7.5 with Python 3.12 or newer
- **THEN** no documentation error is recorded
- **AND** the `integer` and `list` type documentation is available
- **AND** the `id` argument shows the type `ID`

### Requirement: Return types follow Robot Framework's model

A keyword without a return annotation SHALL report no return type on every supported Robot Framework version. A keyword annotated `-> None` SHALL report `None` as its return type when the installed Robot Framework's Libdoc does so (RF ≥ 7.5).

#### Scenario: Keyword without return annotation
- **WHEN** a keyword without a return annotation is documented on RF 7.4 and on RF 7.5
- **THEN** its hover shows no return type on either version

#### Scenario: Keyword annotated with None
- **WHEN** a keyword annotated `-> None` is documented on RF 7.5
- **THEN** its hover shows the return type `None`

### Requirement: Libdoc HTML for Markdown-documented libraries needs the optional markdown package

Generating Libdoc HTML through RobotCode (the documentation web view and `robotcode libdoc`) SHALL work for libraries documented in Markdown when the `markdown` package is installed in the user's environment. The package is optional in Robot Framework and SHALL NOT be a dependency of RobotCode's packages or part of the bundled editor extensions, as for `docutils` and reStructuredText. Without it the request SHALL fail with Robot Framework's message naming the missing module instead of an unhandled failure.

#### Scenario: Documentation web view with markdown installed
- **WHEN** the HTML documentation of `Collections` is requested on RF 7.5 in an environment where `markdown` is installed
- **THEN** the HTML documentation is shown

#### Scenario: Documentation web view without markdown
- **WHEN** the HTML documentation of `Collections` is requested on RF 7.5 in an environment without `markdown`
- **THEN** the documentation web view shows the message `Markdown format requires 'markdown' module to be installed.`
