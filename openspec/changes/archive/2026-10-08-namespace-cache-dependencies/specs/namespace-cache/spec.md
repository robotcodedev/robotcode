# Spec Delta

## Purpose

Defines what a file's analysis restored from RobotCode's namespace disk cache must give compared with a fresh analysis of the same file state, so that features reading the analysis of closed files get the same answers as for open ones.

## ADDED Requirements

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
