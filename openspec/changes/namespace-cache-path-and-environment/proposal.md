# Proposal: namespace-cache-path-and-environment

## Why

A namespace restored from the namespace disk cache can give other diagnostics than a fresh analysis of the same unchanged file when the Python path or an environment variable has changed since it was stored. Reproduced on `main` with `robotcode analyze code` (RF 7.5):

- Suites import `anotherres.resource`, `extravars.py` and `extralib.py`, which only `-P extra` makes findable. A run with `-P extra` stores their namespaces; the next run without `-P` reports no error for them, a run with `--no-cache-namespaces` reports each of the three imports and the keyword or variable it provides as not found. Imports by module name (`Variables extramodvars`, `Library extramodlib`) are reported correctly. The language server uses the same restore for closed files, so a removed `python-path` entry, a changed `robotcode.robot.pythonPath` or PyCharm's source roots switched off leave closed files with their old analysis.
- `Resource ${CURDIR}/../%{RESDIR}/anotherres.resource`: after `RESDIR` in `[env]` of robot.toml changes from `extra` to `nowhere`, the next run reports nothing, a fresh analysis the missing resource file and its keyword.
- `Log %{MY_VAR}`: after `MY_VAR` is removed from `[env]`, the next run reports nothing, a fresh analysis `EnvironmentVariableNotFound`.
- `VAR ${NAME_%{SUFFIX}} value` and `Log ${NAME_a}`: after `SUFFIX` changes from `a` to `b`, the next run reports nothing, a fresh analysis `${NAME_a}` as not found.

The restore already resolves the imports again (`Namespace.from_data`), but it neither looks at the result nor searches resource files: it takes the stored path of a resource file as long as the file exists. Environment variables used in the rest of the file are only looked at by the analysis that the restore skips. The part of the configuration fingerprint meant for environment variables never takes effect, and it could not tell which variables a file uses anyway.

## What Changes

- A namespace whose imports, resolved again when it is restored, no longer find a file or find other files than the ones it was stored with is analyzed again instead of being restored. Resource files are searched again like library and variable files, instead of taking the stored path. This covers every source of the Python path and of environment variables in import paths: `-P`, `python-path` in robot.toml, the editor settings, PyCharm's roots, the shell.
- The analysis records the environment variables it looks up outside the imports: for each reference without a default value whether the variable is set, and, where it uses the value (a variable name built from an environment variable, such as `${NAME_%{SUFFIX}}`), a hash of the value. A namespace whose recorded variables are set, unset or valued differently now is analyzed again. References with a default value (`%{NAME=default}`) are not recorded, and only hashes, no values, are stored.
- The environment part of the configuration fingerprint is removed; the recorded lookups replace it.
- The Python path does not become part of the fingerprint: an unrelated change of the Python path, or a language server and `robotcode analyze code` started with different paths, do not make every namespace analyze again.
- The analysis cache stores other data than before (no stored resource paths, the recorded lookups); as with every version, entries of other RobotCode versions are not read.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `namespace-cache`: A restored namespace must match a fresh analysis also after changes of the Python path and of environment variables. New requirements for imports that find another file or none, and for environment variables the analysis of the file looked up; the requirement on restoring unchanged namespaces states which changes of environment variables do not keep a namespace from being restored.

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/document_cache_helper.py`: the restore checks the result of the import resolution.
- `packages/robot/src/robotcode/robot/diagnostics/namespace.py`, `import_resolver.py`, `entities.py`, `imports_manager.py`: the stored resource paths and their plumbing go; `NamespaceMetaData` gets the recorded lookups, `validate_namespace_meta` compares them, the configuration fingerprint loses its environment part.
- `packages/robot/src/robotcode/robot/diagnostics/analyzer_result.py`, `namespace_analyzer.py`, `semantic_analyzer/analyzer.py`: both analyzers record the environment variables they look up.
- Tests: new tests for `robotcode analyze code` with two runs, a language server restart scenario in `tests/robotcode/language_server/robotframework/test_namespace_cache_restart.py`, unit tests in `tests/robotcode/robot/diagnostics/test_namespace_cache.py`.
- Docs: one sentence in `docs/src/content/docs/guides/analyzing-code.md` on when a cached analysis is not used.
- Related open changes: `env-var-check-nested-names` changes when the `NamespaceAnalyzer` checks an environment variable; the recording follows that check. `semantic-model-cleanup` deletes the `NamespaceAnalyzer` and its part of the recording.
