# namespace-cache Specification

## Purpose

Defines what a file's analysis restored from RobotCode's namespace disk cache must give compared with a fresh analysis of the same file state, so that features reading the analysis of closed files get the same answers as for open ones.

## Requirements

### Requirement: Restored references to imports match the fresh analysis

A namespace restored from the namespace disk cache SHALL have the same references to imports as a fresh analysis of the same file state. For every import the fresh analysis has an entry for, the restored namespace SHALL have an entry with the same importing file, import line and alias, and with the same referencing locations. This holds also when the file imports something that is already loaded implicitly or through a resource file.

#### Scenario: Explicit import of BuiltIn

- **WHEN** a suite imports `BuiltIn` explicitly and its namespace is restored from the cache
- **THEN** the restored namespace has the entry of that import with its import line, as the fresh analysis has

#### Scenario: Explicit BuiltIn import and a call with the BuiltIn prefix

- **WHEN** a suite imports `BuiltIn` explicitly and calls `BuiltIn.Log`, and its namespace is restored from the cache
- **THEN** the restored namespace has both entries of the fresh analysis, the import and the implicit `BuiltIn`, each with its own locations

#### Scenario: Library imported directly after a resource file that imports it

- **WHEN** `lib.resource` imports `Collections`, a suite imports `lib.resource` and then `Collections`, and the suite's namespace is restored from the cache
- **THEN** the restored namespace has the entry of the suite's direct import with its import line, not only the entry of the import in `lib.resource`

#### Scenario: Variable file imported directly after a resource file that imports it

- **WHEN** `lib.resource` imports `vars.py`, a suite imports `lib.resource` and then `vars.py`, and the suite's namespace is restored from the cache
- **THEN** the restored namespace has the entry of the suite's direct import of `vars.py`

#### Scenario: Library imported with other arguments than in a resource file

- **WHEN** `lib.resource` imports `./arglib.py` with the argument `a`, a suite imports `lib.resource` and then `./arglib.py` with the argument `b`, and the suite's namespace is restored from the cache
- **THEN** the restored namespace has the entry of the suite's import with the argument `b`

### Requirement: A namespace is not restored when a file it depends on changed

RobotCode SHALL NOT restore a namespace from the namespace disk cache when a library file, variable file or resource file that its analysis used has changed since the namespace was stored. Each such file SHALL count as a dependency of its own, also when another file the analysis used is imported with the same name from another folder.

#### Scenario: Variable file with the same name as another one changed

- **WHEN** a suite imports `vars.py`, then a resource file `sub/r.resource` that imports `sub/vars.py`, the suite's namespace is stored in the cache, and the suite's `vars.py` loses the variable `${TOP}` before the next session
- **THEN** the suite is analyzed again in the next session and reports `${TOP}` as not found

#### Scenario: Library file with the same name as another one changed

- **WHEN** a suite imports the library `helper.py`, then a resource file `sub/r.resource` that imports `sub/helper.py`, the suite's namespace is stored in the cache, and the suite's `helper.py` loses the keyword `Top Kw` before the next session
- **THEN** the suite is analyzed again in the next session and reports `Top Kw` as not found

### Requirement: A namespace is restored while the files it depends on are unchanged

RobotCode SHALL restore a namespace from the namespace disk cache when the file itself and none of the library files, variable files and resource files its analysis used have changed since it was stored. Files with the same import names in other folders SHALL NOT keep it from being restored.

#### Scenario: Nothing changed

- **WHEN** a suite imports the resource file `sub/r.resource`, which imports `sub/vars.py`, then `vars.py`, its namespace is stored in the cache, and no file changes before the next session
- **THEN** the suite's namespace is restored from the cache in the next session
