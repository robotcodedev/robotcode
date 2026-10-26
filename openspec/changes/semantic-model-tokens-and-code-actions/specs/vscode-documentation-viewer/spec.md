# Spec Delta

## MODIFIED Requirements

### Requirement: Documented import of a call with a prefix

For a keyword call with a library or resource prefix (`lib_var.A Library Keyword`), the documentation actions SHALL document the import the prefix names: on the keyword name at that keyword, on the prefix the page of that import without going to a keyword, as the hover shows it there. When the same library is imported twice with different arguments, a call through the second import's alias SHALL use the second import's arguments.

#### Scenario: First import of the same library
- **WHEN** a suite imports `alibrary` with `a_param=from hello` as `lib_hello` and with `a_param=from lib` as `lib_var`, and the user chooses "Show in Documentation Viewer" on `A Library Keyword` in `lib_hello.A Library Keyword`
- **THEN** the viewer's target field shows `alibrary::a_param=from hello#a-library-keyword`

#### Scenario: Prefix of the call
- **WHEN** the suite above is open and the user chooses "Show in Documentation Viewer" on `lib_hello` in `lib_hello.A Library Keyword`
- **THEN** the viewer's target field shows `alibrary::a_param=from hello`, and the viewer shows `alibrary` from its beginning

#### Scenario: Prefix BuiltIn
- **WHEN** the user chooses "Show in Documentation Viewer" on `BuiltIn` in `BuiltIn.Log    x`
- **THEN** a viewer shows `BuiltIn` from its beginning, not at `Log`

## ADDED Requirements

### Requirement: Documentation actions on the alias of a Library import

On the alias of a Library import, after `AS` (Robot Framework 6.0 and newer) or `WITH NAME`, the documentation actions SHALL be offered and SHALL document that import as on its name, as the link of the hover there does.

#### Scenario: Alias after AS
- **WHEN** the user chooses "Show in Documentation Viewer" on `Coll` in `Library    Collections    AS    Coll`, on Robot Framework 6.0 or newer
- **THEN** a viewer shows `Collections` from its beginning

### Requirement: Documentation actions for a selection

With a selection instead of a cursor, the documentation actions SHALL be offered when the selection lies within one name where a cursor gets them: the name or alias of an import, the keyword reference of a call, setup, teardown or template, or the name in a keyword definition header. A selection within the prefix of a call SHALL document the import, any other selection within the reference the keyword. A selection beyond the name SHALL get no actions.

#### Scenario: Selected keyword name
- **WHEN** source actions are requested with `Log` selected in `Log    hello`
- **THEN** the three documentation actions are offered, for `BuiltIn` at `Log`

#### Scenario: Selected call with a prefix
- **WHEN** the user selects `BuiltIn.Log` in `BuiltIn.Log    hello` and chooses "Show in Documentation Viewer"
- **THEN** a viewer shows `BuiltIn` at `Log`

#### Scenario: Selection beyond the name
- **WHEN** source actions are requested with `Log    hello` selected in the step `Log    hello`
- **THEN** no documentation action is offered

#### Scenario: Selected import name
- **WHEN** source actions are requested with `Collections` selected in `Library    Collections`
- **THEN** the three documentation actions are offered, for the library `Collections`
