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

RobotCode SHALL restore a namespace from the namespace disk cache when the file itself and none of the library files, variable files and resource files its analysis used have changed since it was stored, its imports find the same files and the environment variables its analysis looked up are as they were. Files with the same import names in other folders, environment variables used only with a default value and values the analysis did not use SHALL NOT keep it from being restored.

#### Scenario: Nothing changed

- **WHEN** a suite imports the resource file `sub/r.resource`, which imports `sub/vars.py`, then `vars.py`, its namespace is stored in the cache, and no file changes before the next session
- **THEN** the suite's namespace is restored from the cache in the next session

#### Scenario: Default value and new value of environment variables

- **WHEN** a suite logs `%{OPTIONAL=fallback}` and `%{MY_VAR}`, a run with `OPTIONAL` unset and `MY_VAR` set to `x` stores its namespace, and before the next run `OPTIONAL` is set and `MY_VAR` is set to `y`
- **THEN** the next run restores the suite's namespace from the cache

#### Scenario: Python path entry added that the imports do not use

- **WHEN** a suite imports `anotherres.resource` from the Python path entry `extra`, a run with `-P extra` stores its namespace, and the next run adds `-P other`, a folder without files of the suite's imports
- **THEN** the next run restores the suite's namespace from the cache

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

### Requirement: A restored semantic model refers to the keywords and imports of the restored namespace

With the semantic-model analysis path enabled, a namespace restored from the namespace disk cache SHALL resolve the keyword calls, imports and template rows of its semantic model to the same keywords and imports as a fresh analysis of the same file state, with their library or resource documentation. The features that read them SHALL answer as for a fresh analysis, also after the file is opened in the editor with unchanged text.

#### Scenario: BuiltIn keyword after a restart

- **WHEN** a suite calls `Log`, its namespace is restored from the cache with the semantic-model path enabled, and the suite is then opened in the editor without changes
- **THEN** the documentation target at `Log` is `BuiltIn` with the keyword `Log`, as for a fresh analysis

#### Scenario: Library import and a call with its prefix

- **WHEN** a suite imports `Collections` and calls `Collections.Append To List`, and its namespace is restored from the cache with the semantic-model path enabled
- **THEN** the documentation targets at the import and at the call are those of a fresh analysis

### Requirement: A namespace is not restored when an import finds another file or none

RobotCode SHALL NOT restore a namespace from the namespace disk cache when one of its imports, resolved with the current Python path and environment variables, finds no file or another file than when the namespace was stored. This holds for resource files and for libraries and variable files imported by path, whatever sets the Python path or the environment variable: a command line option, robot.toml, the editor settings or the shell.

#### Scenario: Python path entry removed between two runs

- **WHEN** suites import `anotherres.resource`, `extravars.py` and `extralib.py`, which only the Python path entry `extra` makes findable, `robotcode analyze code -P extra` stores their namespaces, and the next run has no `-P`
- **THEN** the next run reports the three imports as not found, as a run with an empty cache does

#### Scenario: Import finds a file of the same name in another folder

- **WHEN** a suite imports `common.resource` and calls `A Kw`, `a/common.resource` defines `A Kw` and `b/common.resource` defines `B Kw`, a run with `-P a` stores the suite's namespace, and the next run uses `-P b`
- **THEN** the next run reports `A Kw` as not found

#### Scenario: Environment variable in an import path changed

- **WHEN** a suite imports `${CURDIR}/../%{RESDIR}/anotherres.resource`, a run with `RESDIR` set to `extra` stores the suite's namespace, and `RESDIR` is set to a folder without that file before the next run
- **THEN** the next run reports the resource file as not found

#### Scenario: Python path setting changed while the language server is stopped

- **WHEN** a closed suite imports `anotherres.resource`, which only the entry `extra` of the setting `robotcode.robot.pythonPath` makes findable, a language server session stores the suite's namespace, and the entry is removed before the next session
- **THEN** the next session reports the resource file as not found for the closed suite

### Requirement: A namespace is not restored when an environment variable it uses has changed

RobotCode SHALL NOT restore a namespace from the namespace disk cache when an environment variable that the analysis of the file looked up without a default value is set now and was not set when the namespace was stored, or the other way round. Neither SHALL it restore the namespace when an environment variable whose value the analysis used, such as in the name of a variable, has another value now. This holds whatever sets the variable: robot.toml, the editor settings or the shell.

#### Scenario: Environment variable removed

- **WHEN** a suite logs `%{MY_VAR}`, a run with `MY_VAR` set in `[env]` of robot.toml stores the suite's namespace, and `MY_VAR` is removed from robot.toml before the next run
- **THEN** the next run reports `%{MY_VAR}` as not found

#### Scenario: Environment variable set in the shell

- **WHEN** a suite logs `%{MY_VAR}`, a run without `MY_VAR` reports it as not found, and `MY_VAR` is set in the shell before the next run
- **THEN** the next run reports no error for `%{MY_VAR}`

#### Scenario: Variable name built from an environment variable

- **WHEN** a test sets `VAR    ${NAME_%{SUFFIX}}    value` and logs `${NAME_a}`, a run with `SUFFIX` set to `a` stores the suite's namespace, and `SUFFIX` is set to `b` before the next run
- **THEN** the next run reports `${NAME_a}` as not found
