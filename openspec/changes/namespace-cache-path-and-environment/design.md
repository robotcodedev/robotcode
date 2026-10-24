# Design: namespace-cache-path-and-environment

## Context

See proposal.md for the failures. How a namespace comes from the disk cache today:

1. `DocumentsCacheHelper._try_load_cached_namespace` reads the entry.
2. `ImportsManager.validate_namespace_meta` compares the file's `DiskInfo`, the configuration fingerprint and the dependency metas. Dependencies are keyed by the resolved file (`res:<path>`, `lib:`/`var:` + the meta's cache key: a path, or a module name). For a path it checks only that the file at that path is unchanged; a module name is resolved again, which is why imports by module name already behave.
3. `Namespace.from_data` resolves the imports again (Phase 1+2, `ImportResolver.resolve(data.imports, source_hints=data.resolved_resource_sources)`) and rebuilds the namespace with the cached Phase 3 results: diagnostics, references, the semantic model.

The gaps:

- The result of step 3 is not looked at. `failed_imports` and `dependency_metas` of the restore are kept on the namespace, and the cached diagnostics are returned even when an import is not found any more.
- Resource imports skip the search: `ImportResolver._import_resource` takes the stored path whenever that file exists (`import_resolver.py`, the source hints added in 1d4ba6b7).
- The analyzers read the environment in Phase 3, which the restore skips, in two places each:
  - the existence check of a reference without a default value, in `_handle_find_variable_result` (`namespace_analyzer.py`, `semantic_analyzer/analyzer.py`);
  - the value of a variable used in a variable name (`${NAME_%{SUFFIX}}`), in `_resolve_variable_to_string`, which `_try_resolve_nested_variable_base` calls.

  Both read `os.environ` directly. Import names are resolved by the `ImportResolver` with Robot Framework's variable replacement, also from `os.environ`.
- The environment part of the fingerprint, `(k, v) for k, v in self._environment.items() if k not in os.environ` (`imports_manager.py`), is empty in practice. The CLI (`evaluated_with_env`) and the language server (`_on_initialize`, `server_initialized`) write the configured variables into `os.environ` before the `ImportsManager` is created.

Measured with a prototype that patched the restore at runtime. Setup: a synthetic project of 451 files (400 suites, 51 resource files, imports through `python-path`), warm library and resource caches, `robotcode analyze code`, three runs each.

| Variant | Analysis time | Cache hits |
|---|---|---|
| Today | 1.5–1.7 s | 451/451 |
| Checking the result of step 3, resource paths still taken from the cache | 1.5–1.7 s | 451/451 |
| Checking the result, resources searched | 1.6 s | 451/451 |
| Parse, own `ResourceDoc` and Phase 1+2 a second time on every hit | 2.8 s | 451/451 |
| Full analysis without the namespace cache | 3.4 s | – |

With the check and the search, the cases of the proposal give what a fresh analysis gives: 10 instead of 4 errors without `-P`, 2 instead of 0 for the changed `RESDIR`. The environment variable in the test body stays at 0 errors without D3.

## Goals / Non-Goals

**Goals:**

- A restored namespace gives what a fresh analysis gives after changes of the Python path and of environment variables, from whatever source.
- The path of a hit stays as fast as today, within about 0.1 s per 450 files.
- `robotcode analyze code` and the language server keep sharing cache entries whenever their imports find the same files.

**Non-Goals:**

- Variable files and libraries whose Python code reads environment variables when it is imported. The cache tracks their files, as before.
- Which environment variable references the analyzers check. That is the subject of `env-var-check-nested-names`; the recording sits inside the check and follows it.
- Namespaces of open documents and the language server's invalidation on file events. Only the restore from the disk cache changes.

## Decisions

### D1: The restore checks the result of its own import resolution

`_try_load_cached_namespace` treats a restored namespace as a cache miss when its `failed_imports` is not empty, or when the keys of its `dependency_metas` differ from those of `meta.dependency_fingerprints`. The miss is logged at debug level like the other misses.

- The check costs nothing measurable, because the resolution runs anyway (table above).
- A failed import at restore time always means a change: a namespace with a failed import is never stored.
- The dependency keys name the resolved files, so an import that now finds another file gives another key.
- The check sits in `_try_load_cached_namespace`, which holds the meta; `from_data` stays a reconstruction.

Alternatives:

- The Python path in the fingerprint: every unrelated change of the Python path analyzes every file again, and so does every switch between the CLI and the language server of VS Code, whose `sys.path` differs because it runs the bundled robotcode. It does not cover environment variables in import paths either.
- Running the import phase a second time: 2.8 s instead of 1.6 s, for the same answer.
- Storing the import names after variable replacement and searching them again: needs more stored data, and environment variables in import paths would need a check of their own.

### D2: Resource files are searched again

The stored resource paths are dropped. The resolution searches a resource file with the current Python path and environment variables, as it already does for libraries and variable files.

- The shortcut is exactly what misses a moved or vanished resource.
- Checking a stored path would need the same search.
- The search costs 0.05–0.1 s per 450 files, because `ImportsManager` keeps the found files per name and folder.

Removed with it:
- `NamespaceData.resolved_resource_sources` and where the data export fills it;
- `source_hints` of `ImportResolver.resolve` and `ImportResolver._source_hints`;
- `Import.hint_key`, which nothing else uses;
- the `source` keyword of `ImportsManager.get_resource_doc_for_resource_import`, `get_resource_doc_for_resource_import_with_meta`, `get_namespace_and_libdoc_for_resource_import` and `_get_entry_for_resource_import`. It is older than the stored paths (25ef49c3), but they were its last user.

The other parts of 1d4ba6b7 stay: only top-level imports are stored, and paths are normalized as strings.

### D3: The analyzers record the environment variables they read

Each analyzer records where it reads the environment:
- the existence check of a reference without a default value records the name and whether the variable is set;
- `_resolve_variable_to_string` records the name and the SHA-256 of the value, or that the variable is not set.

The records pass through `AnalyzerResult` and `Namespace` into two new maps of `NamespaceMetaData`, one for presence and one for value hashes. `validate_namespace_meta` compares them with `os.environ` in its first, cheap level, before the dependency checks.

Why it is recorded where the analysis reads:
- Every source counts, because the analyzers read `os.environ` and nothing else.
- The record has exactly the variables the result depends on.
- The stored references cannot replace it: `EnvironmentVariableDefinition.default_value` does not take part in comparisons, so `%{X}` and `%{X=a}` of one file end up as one reference entry, and the stored default is either one.

Why a hash and not the value: no environment value, such as a token or a password, ends up in the cache file. SHA-256 of the UTF-8 encoded value is the same in every process, unlike Python's `hash()`.

Not recorded:
- variables in import names: D1 and D2 resolve those with the current values;
- references with a default value: the analysis does not depend on them.

Both analyzers record. The `NamespaceAnalyzer`'s part goes away with `semantic-model-cleanup`. A new place that reads the environment in Phase 3 has to record too; a comment at both read sites says so.

Alternatives:
- Deriving the names from the stored references: the default is lost (see above).
- Storing values: they would put secrets on disk.
- The whole environment in the fingerprint: every difference between shells and IDEs would analyze everything again.

### D4: The environment part of the fingerprint goes

It never takes effect, and D3 replaces it. `ImportsManager._environment` and its `environment` property stay; environment variable completion lists their names.

### D5: Cache layout

`NamespaceMetaData` gets fields and `NamespaceData` loses one. Old entries need no handling: each RobotCode version gets its own cache, and the development caches in the repository are cleared once after the change.

## Risks / Trade-offs

- [The restore can be rejected after `from_data` has done its work] → That work is the resolution measured above, about 3 ms per file. A rejected entry is replaced by the entry of the fresh build.
- [The restore resolves differently from the build for unchanged inputs and misses spuriously] → Both use the same `ImportResolver`, and the measurement kept all 451 hits. The synthetic project has no variables in import names; the tests import with `${CURDIR}` and `%{…}` in the path.
- [The analysis uses environment values somewhere else] → Checked: in the diagnostics package the analyzers read `os.environ` only at the two places per analyzer named in Context. Imports are covered by D1 and D2.
- [`%{%{N}}`: the value of `N` names the variable that is checked] → The inner lookup records the value hash of `N`, so a new value of `N` analyzes again.
- [The restart tests see a restore as "`Namespace.from_data` was called"] → `from_data` now also runs for an entry that is rejected afterwards. The helper `_session` in `test_namespace_cache_restart.py` instead takes "the suite's namespace was not built" as restored.
