# Spec Delta

## Purpose

Defines what a file's analysis restored from RobotCode's namespace disk cache must give compared with a fresh analysis of the same file state, so that features reading the analysis of closed files get the same answers as for open ones.

## ADDED Requirements

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
