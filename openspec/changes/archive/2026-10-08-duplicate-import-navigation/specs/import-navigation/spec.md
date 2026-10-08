# Spec Delta

## Purpose

Defines what the language server gives on the name of a `Library`, `Resource` or `Variables` import: hover, Go to Definition and Find References. This includes imports of something the file already imports, directly or through a resource file.

## ADDED Requirements

### Requirement: A repeated resource import is navigable

On the name of a `Resource` import of a resource file that the importing file already imports, hover SHALL give the same result as on the import that imported it first. Go to Definition SHALL behave as on a repeated `Library` or `Variables` import: a second import in the same file leads to the first one, and an import of a file that came in through another resource file opens that file. The import SHALL still report that the resource file is already imported.

#### Scenario: Resource file imported twice

- **WHEN** a suite imports `a.resource` in two `Resource` lines and the user hovers over the name in the second line
- **THEN** the hover shows the resource file `a`, Go to Definition on the same name leads to the first `Resource` line of the suite, and the second line reports that `a.resource` is already imported

#### Scenario: Resource file imported again after a resource file that imports it

- **WHEN** a suite imports `b.resource`, which imports `a.resource`, and then imports `a.resource` directly
- **THEN** hover and Go to Definition on `a.resource` in the suite's direct import show and open `a.resource`

### Requirement: Find References lists every import statement once

Find References on the name of a `Library`, `Resource` or `Variables` import SHALL list every import statement in the workspace that imports the same library, resource file or variable file. That includes statements that import it again, directly or after a resource file that imports it, and statements with other arguments or an alias. No location SHALL appear twice in the result.

#### Scenario: Library imported again with an alias

- **WHEN** a suite imports `Collections` and then `Collections    WITH NAME    Coll2` (or, since Robot Framework 6.0, `AS    Coll2`), and the user runs Find References on either import
- **THEN** each of the two import lines appears exactly once in the result

#### Scenario: Library imported directly after a resource file that imports it

- **WHEN** `lib.resource` imports `Collections`, a suite imports `lib.resource` and then `Collections`, and the user runs Find References on any import of `Collections`
- **THEN** the result contains the import line in `lib.resource` and the suite's direct import line

#### Scenario: Variable file imported twice

- **WHEN** a suite imports `vars.py` in two `Variables` lines
- **THEN** Find References on either import lists both lines

#### Scenario: Resource file imported twice

- **WHEN** a suite imports `a.resource` in two `Resource` lines
- **THEN** Find References on either import lists both lines, each once

#### Scenario: Import that is not repeated

- **WHEN** a suite imports `OperatingSystem` twice without an alias and calls `OperatingSystem.Log File`
- **THEN** Find References on either import lists both import lines and the call, each once, as before

### Requirement: Find References on a resource import finds its prefixed calls in every file

Find References on the name of a `Resource` import SHALL list the keyword calls that use the resource file's name as prefix, such as `a.A Keyword`, in every file of the workspace that imports the resource file, as it does for the prefixed calls of a library.

#### Scenario: Prefixed calls in two suites

- **WHEN** two suites import `a.resource` and both call `a.A Keyword`, and the user runs Find References on the import in the first suite
- **THEN** the result contains the call in the first suite and the call in the second suite

### Requirement: Find References works from a repeated import

Find References on the name of an import that imports a library, resource file or variable file the file already imports SHALL give the same result as on the import that imported it first.

#### Scenario: From the repeated resource import

- **WHEN** a suite imports `b.resource`, which imports `a.resource`, then imports `a.resource` directly, and the user runs Find References on the direct import
- **THEN** the result is the same as for Find References on the import of `a.resource` in `b.resource`, and it is not empty
