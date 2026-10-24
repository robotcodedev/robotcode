## ADDED Requirements

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

## MODIFIED Requirements

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
