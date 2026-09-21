# Spec Delta

<!-- Modifies requirements introduced by the change support-rf75 (archive support-rf75 first). -->

## MODIFIED Requirements

### Requirement: Tags declared in documentation are extracted

RobotCode SHALL treat tags declared in keyword documentation — the `Tags:` section of a Python keyword docstring and of a resource keyword's `[Documentation]` — as keyword tags, merged with tags declared via `[Tags]` or `robot_tags`. A keyword whose merged tags contain `robot:private` SHALL be private. In resource keywords a documentation tag written as `-name` SHALL remove `name` from the merged tags on Robot Framework ≥ 7.4 (the first version whose Libdoc does so; older versions keep it literally); in library keywords it SHALL be kept literally. The `Tags:` section SHALL NOT appear in the rendered documentation text, in any form the installed Robot Framework recognises (every `Tags:` section on RF ≥ 7.5, a trailing `Tags:` line on older versions). Tags and privacy SHALL be the ones Robot Framework's own Libdoc reports for the installed version, identical on RF 7.4 and RF 7.5.

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

## REMOVED Requirements

### Requirement: Documentation content is never dropped
**Reason**: Google-style `Args:`, `Returns:` and `Raises:` sections now have a dedicated rendering (see capability `keyword-documentation-rendering`), so they are separated from the documentation text instead of being kept in it.
**Migration**: None for users; the content moves from the documentation text into the argument, return and raises blocks of the rendered documentation.

## ADDED Requirements

### Requirement: Google-style sections become structured documentation

On Robot Framework ≥ 7.5 RobotCode SHALL separate the `Args:`, `Returns:` and `Raises:` sections (with the section names Robot Framework accepts) from a keyword's documentation into per-argument descriptions, a return description and a list of raised exceptions with descriptions, for library keywords and for resource keywords, without modifying Robot Framework's objects. The remaining documentation text SHALL no longer contain those sections. On older versions the documentation text SHALL stay unchanged and the structured fields SHALL be empty. A description for an argument the keyword does not have (for example a name accepted through `**kwargs`) SHALL NOT cause an error and SHALL be kept with the argument descriptions.

#### Scenario: Library keyword with Google-style sections
- **WHEN** a Python keyword `paint(shade, *items)` documents `Args:` for `shade` and `*items`, `Returns:` and `Raises: ValueError` and the library is documented on RF 7.5
- **THEN** the argument descriptions, the return description and the exception with its description are available on the keyword's documentation model
- **AND** the documentation text contains none of the section headers

#### Scenario: Resource keyword with Google-style sections
- **WHEN** a resource keyword's `[Documentation]` contains `Args:` with `${name}: Who to greet.` on RF 7.5
- **THEN** the description is available for the argument `name`

#### Scenario: Older Robot Framework
- **WHEN** the same library is documented on RF 7.4
- **THEN** the documentation text is unchanged and no argument, return or raises descriptions exist

#### Scenario: Live objects stay untouched
- **WHEN** the documentation of a library loaded by a running REPL session is rendered on RF 7.5
- **THEN** the session's keyword objects keep their original documentation and argument specification

### Requirement: Argument types resolve to type documentation

For every keyword argument and for the return type, RobotCode SHALL record the mapping from the used type names to the names of the corresponding type documentation, as Robot Framework's Libdoc computes it (Robot Framework ≥ 6.1), and SHALL use it to look up type documentation for signature help and completion. An argument typed with an alias of an enum or TypedDict SHALL resolve to that enum's or TypedDict's documentation, and a standard type whose documentation name differs from the type name (`int` → `integer`, `str` → `string`) SHALL resolve as well.

#### Scenario: Aliased enum argument
- **WHEN** a library defines `type Shade = Color` for an `Enum` `Color` and a keyword argument `shade: Shade`, on RF 7.5 with Python 3.12 or newer
- **THEN** the argument shows the type `Shade`
- **AND** signature help and value completion for `shade` show the `Color` enum documentation with its members

#### Scenario: Standard type name differs from documentation name
- **WHEN** signature help is requested for a library keyword argument annotated `int` on RF 6.1 or newer
- **THEN** the `integer` type documentation is shown
