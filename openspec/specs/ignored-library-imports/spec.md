# ignored-library-imports Specification

## Purpose

Defines what RobotCode reports when Robot Framework would ignore a `Library` import because an earlier import already uses the name it is imported under, so that the user sees in the editor and in `robotcode analyze code` what Robot Framework warns about only when the suite runs.

## Requirements

### Requirement: An import of another library under a used name is reported

On Robot Framework 7.4 and newer, a `Library` import of the analyzed file SHALL report the warning `LibraryImportIgnored` when the name it is imported under (its alias, otherwise its library name) is already used by an earlier import with another library name. The warning SHALL say that the import is ignored because another library with that name is already imported, and SHALL point to the earlier import when that has an import statement.

#### Scenario: Name used as an alias before

- **WHEN** a suite has `Library    Collections    AS    helper` and then `Library    helper.py`
- **THEN** the second import reports `LibraryImportIgnored` for the name `helper`, pointing to the first import

#### Scenario: Earlier import in a resource file

- **WHEN** a suite imports `r.resource`, which has `Library    Collections    AS    helper`, and then has `Library    helper.py`
- **THEN** the suite's `Library    helper.py` reports `LibraryImportIgnored`, pointing to the import in `r.resource`

#### Scenario: Alias that is the name of a default library

- **WHEN** a suite has `Library    Collections    AS    BuiltIn`
- **THEN** the import reports `LibraryImportIgnored` for the name `BuiltIn`

### Requirement: An import of a library with other arguments under a used name is reported

On Robot Framework 7.4 and newer, a `Library` import of the analyzed file SHALL report the warning `LibraryImportIgnored` when the name it is imported under is already used by an earlier import with the same library name but different arguments. The warning SHALL say that the library is already imported with different arguments and SHALL point to the earlier import. Arguments that resolve to the same values SHALL count as the same.

#### Scenario: Other argument than in a resource file

- **WHEN** `lib.resource` has `Library    ./arglib.py    a`, and a suite imports `lib.resource` and then has `Library    ./arglib.py    b`
- **THEN** the suite's import reports `LibraryImportIgnored`, saying that `arglib` is already imported with different arguments

#### Scenario: Same value through a variable

- **WHEN** a suite sets `${MODE}` to `a` in its `*** Variables ***` section and has `Library    ./arglib.py    ${MODE}` and then `Library    ./arglib.py    a`
- **THEN** no `LibraryImportIgnored` is reported

### Requirement: An ignored import in a resource file is reported at the Resource import

On Robot Framework 7.4 and newer, when a `Library` import in a resource file that the analyzed file imports, directly or through other resource files, is ignored for one of the reasons above, the analyzed file SHALL report `LibraryImportIgnored` at its own `Resource` import that brings in that resource file. The warning SHALL name the ignored library and the resource file it is imported in and SHALL point to the ignored import.

#### Scenario: Name used by the suite

- **WHEN** a suite has `Library    Collections    AS    helper` and then `Resource    r.resource`, and `r.resource` has `Library    helper.py`
- **THEN** the suite's `Resource    r.resource` reports `LibraryImportIgnored`, pointing to `Library    helper.py` in `r.resource`

#### Scenario: Through another resource file

- **WHEN** a suite has `Library    Collections    AS    helper` and then `Resource    outer.resource`, `outer.resource` imports `inner.resource`, and `inner.resource` has `Library    helper.py`
- **THEN** the suite's `Resource    outer.resource` reports `LibraryImportIgnored`, pointing to `Library    helper.py` in `inner.resource`

#### Scenario: Both imports in the same resource file

- **WHEN** `common.resource` has `Library    Collections    AS    helper` and then `Library    helper.py`, and two suites import `common.resource`
- **THEN** the analysis of `common.resource` reports `LibraryImportIgnored` at its `Library    helper.py`
- **AND** each suite reports it at its `Resource    common.resource`, as Robot Framework warns once for each suite

### Requirement: No warning where Robot Framework does not warn

RobotCode SHALL NOT report `LibraryImportIgnored` on Robot Framework 7.3 and older, when the earlier import has the same library name and the same arguments, also when it imports another file of the same name, and when the ignored import or the earlier import fails to load.

#### Scenario: Robot Framework 7.3

- **WHEN** Robot Framework 7.3 is used and a suite has `Library    Collections    AS    helper` and then `Library    helper.py`
- **THEN** no `LibraryImportIgnored` is reported

#### Scenario: Same library name and arguments from another file

- **WHEN** a suite has `Library    helper.py` and then `Resource    sub/r.resource`, and `sub/r.resource` has `Library    helper.py`, which is `sub/helper.py`
- **THEN** no `LibraryImportIgnored` is reported

#### Scenario: Same library imported twice

- **WHEN** a suite has `Library    Collections` twice
- **THEN** the second import reports `LibraryAlreadyImported` as before and no `LibraryImportIgnored`

#### Scenario: Library that fails to load

- **WHEN** a suite has `Library    Collections    AS    helper` and then `Library    broken.py    AS    helper`, and the module `broken.py` raises an error when it is imported
- **THEN** the second import reports the error of loading `broken.py` and no `LibraryImportIgnored`
