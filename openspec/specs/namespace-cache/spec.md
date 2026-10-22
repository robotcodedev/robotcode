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

### Requirement: The cache keeps no entries of deleted files

The analysis cache SHALL NOT keep the entries of a Robot Framework file after the file was deleted. The language server SHALL remove them when it notices the deletion. `robotcode analyze code` SHALL remove, after its run, the entries of files that no longer exist, also of files outside the paths it analyzed, and SHALL keep the entries of files that still exist.

#### Scenario: File deleted while the language server runs

- **WHEN** a suite is deleted while the language server runs, and the server notices the deletion
- **THEN** `robotcode analyze cache list` lists no entry of that suite

#### Scenario: File deleted between two runs of the analyzer

- **WHEN** a suite is deleted after a run of `robotcode analyze code`, and `robotcode analyze code` runs again
- **THEN** after that run `robotcode analyze cache list` lists no entry of the deleted suite

#### Scenario: Analyzer run on some of the paths

- **WHEN** `robotcode analyze code` runs on `tests/area_a` only
- **THEN** the entries of existing files in `tests/area_b` stay in the cache

### Requirement: The cache keeps no analysis with failed imports

The analysis cache SHALL NOT store the analysis of a file with an import that failed, so that a file created after that analysis is found when the file is analyzed again.

#### Scenario: Resource file created between two sessions

- **WHEN** a suite imports `later.resource`, which does not exist yet, and `later.resource` is created before the language server starts again
- **THEN** after the restart the suite no longer reports the missing resource file

### Requirement: A file read with other language settings is read again

RobotCode SHALL NOT use what the analysis cache keeps of a Robot Framework file, its keywords, variables and imports, when the language settings are not the same as when the file was read. The language settings are `languages` in robot.toml and the setting `robotcode.robot.languages`. RobotCode SHALL read the file again with the current language settings.

#### Scenario: Language added between two runs

- **WHEN** `keywords.resource` defines `Mein Keyword` under the German section header `*** Schlüsselwörter ***`, a suite imports it and calls `Mein Keyword`, `robotcode analyze code` runs without language settings, and `languages = ["de"]` is added to robot.toml before the next run
- **THEN** the next run reports neither `keywords.resource` as empty nor `Mein Keyword` as not found

#### Scenario: Language removed between two runs

- **WHEN** the same project is analyzed with `languages = ["de"]` in robot.toml, and the setting is removed before the next run
- **THEN** the next run reports `Mein Keyword` as not found in the suite, as a run with an empty cache does
