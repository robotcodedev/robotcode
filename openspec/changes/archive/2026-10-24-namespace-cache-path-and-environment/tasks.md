# Tasks

## 1. Imports at restore (design D1, D2)

- [x] 1.1 Make `DocumentsCacheHelper._try_load_cached_namespace` treat a namespace restored by `Namespace.from_data` as a cache miss when its `failed_imports` is not empty or the keys of its `dependency_metas` differ from those of `meta.dependency_fingerprints`, with a debug log like the other misses; verify with the tests of 1.4 and 1.5.
- [x] 1.2 Remove the stored resource paths: `NamespaceData.resolved_resource_sources` and where the data export fills it, `source_hints` and `_source_hints` of `ImportResolver`, `Import.hint_key`, and the `source` keyword of `ImportsManager.get_resource_doc_for_resource_import`, `get_resource_doc_for_resource_import_with_meta`, `get_namespace_and_libdoc_for_resource_import` and `_get_entry_for_resource_import`, which nothing else passes; verify that no reference to them is left (`grep`) and that the tests in `tests/robotcode/robot/diagnostics/test_namespace_cache.py` and `tests/robotcode/language_server/robotframework/parts/test_namespace_cache_restore.py` pass.
- [x] 1.3 Change `_session` in `tests/robotcode/language_server/robotframework/test_namespace_cache_restart.py` to count the suite as restored when its namespace was not built (spy on `NamespaceBuilder.build`), because `from_data` now also runs for an entry that is rejected afterwards; verify that the existing restart tests pass.
- [x] 1.4 Add `tests/robotcode/analyze/code/test_code_analyzer_cache_imports.py`, which runs the analysis twice like `test_code_analyzer_languages.py`, restores `sys.path` between the runs (the language provider adds the Python path to it) and detects a restore by the suite's namespace not being built. Cover the scenarios "Python path entry removed between two runs" (resource file, variable file and library imported by path), "Import finds a file of the same name in another folder", "Environment variable in an import path changed" and "Python path entry added that the imports do not use"; verify that they pass with the fix and fail without it.
- [x] 1.5 Add the scenario "Python path setting changed while the language server is stopped" to `test_namespace_cache_restart.py`: the entry `extra` of `robotcode.robot.pythonPath` removed between the two sessions, `sys.path` and the file search's cache of it reset between them; verify that it passes with the fix and fails without it.
- [x] 1.6 Add to the cache section of `docs/src/content/docs/guides/analyzing-code.md`, after the sentence on failed imports, that a cached analysis is not used when an import now finds another file or none, for example after a change of the Python path; verify the page in the docs dev server.

## 2. Environment variables the analysis reads (design D3, D4)

- [x] 2.1 Record in `NamespaceAnalyzer` and `SemanticAnalyzer` the environment variables they read: in the existence check of a reference without a default value the name and whether it is set, in `_resolve_variable_to_string` the name and the SHA-256 of the value or that it is not set; pass both maps through `AnalyzerResult` to `Namespace`, with a comment at each read site that a new one has to record too. Verify with a new `tests/robotcode/robot/diagnostics/test_environment_lookups.py` that runs both analyzers on `%{A}` (set and unset), `%{B=x}` (not recorded), `${NAME_%{S}}` (value hash) and, on Robot Framework 7.0 and newer, with the `SemanticAnalyzer`, which alone resolves the name, `%{%{N}}` (value hash of `N`).
- [x] 2.2 Add the two maps to `NamespaceMetaData`, fill them in `build_namespace_meta`, compare them with `os.environ` in the first level of `validate_namespace_meta` (debug log on a miss), and remove the environment part of the configuration fingerprint and from its docstring; verify with unit tests in `test_namespace_cache.py`: a variable set or unset since, and a new value where the value was used, are misses; unchanged variables, a new value where only presence was recorded, and configured environment variables alone are hits.
- [x] 2.3 Add to `test_code_analyzer_cache_imports.py` the scenarios "Environment variable removed" (`[env]` through `RobotBaseProfile(env=…).evaluated_with_env()`), "Environment variable set in the shell" (`monkeypatch.setenv`), "Variable name built from an environment variable" and "Default value and new value of environment variables" (restored); verify that they pass with the fix and fail without it.
- [x] 2.4 Extend the sentence of 1.6 by environment variables the file uses that were set or unset since; verify the page in the docs dev server.

## 3. Integration

- [x] 3.1 Delete the `.robotcode_cache` folders in the repository once no process has them open (`lsof +D`), then run `hatch run test:test` and `hatch run lint:all`; verify both are green.
- [x] 3.2 Repeat the reproduction of the proposal with `robotcode analyze code` (the four cases, warm cache against `--no-cache-namespaces`) and the timing on a synthetic project like the one in design.md; verify that every case reports what the fresh analysis reports and that a warm run keeps all hits within about 0.1 s of today.

## Workflow follow-up

- Tick K8 in `playground/pycharm-befunde.md` after the commit.
- Archive the change after review; it adds two requirements to `namespace-cache` and changes one.
