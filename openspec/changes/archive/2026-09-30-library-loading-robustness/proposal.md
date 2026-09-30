# Proposal: library-loading-robustness

## Why

Loading a library for the analysis can block far longer than `load-library-timeout`. `_run_in_subprocess` (`packages/robot/src/robotcode/robot/diagnostics/imports_manager.py:1641-1666`) raises its timeout error but then waits in `executor.shutdown(wait=True)` for the worker to finish. With a `Remote` library pointing at a host that drops packets, `robotcode analyze code` took 540 s although the timeout was set to 5 s. With a 1 s timeout and a library that sleeps 5 s, the call returned after 5.3 s. A timed-out load is not remembered either (`imports_manager.py:218-225`, `:284-297`), so every namespace build tries again and blocks again.

A smaller problem adds to this. If a library cannot be instantiated with the import's arguments, `get_library_doc` loads it again without arguments and serves those keywords (`packages/robot/src/robotcode/robot/diagnostics/library_doc.py:2513-2533`). The import only shows the original error (for example "Import definition contains errors."). Nothing says that the keywords shown come from a load without arguments.

A third problem showed up while testing this change in VS Code. The disk cache stores one documentation per library, keyed by its module name or path without the import arguments (`LibraryMetaData.cache_key`, `imports_manager.py:592-600`). Once a library loaded without errors, every other set of arguments gets that stored documentation, also after a restart. A `Library    NoArgumentLib.py    extra` shows no argument error, and a `Remote` with a mistyped URL shows the keywords of the working URL and no connection error. Only Clear Cache and Restart shows the right error.

These problems exist today, independent of any new feature. The parked `library-keyword-set-declaration` builds on the hard timeout, the kept `None` dependency meta (design D2) and the test setup of this change.

## What Changes

The change is limited to these points (maintainer decisions 2026-09-29 and 2026-09-30):

- **Hard timeout.** When `load-library-timeout` expires, the worker process that loads a library or variable file is terminated. The call returns after the timeout, not when the library gives up.
- **Remembered timeout.** A load that times out is kept as an error result in its import entry, as a refused `Remote` connection already is today. It is not retried on every namespace build. It is loaded again when the library's files or the configuration change, or when the language server restarts (for example with Clear Cache and Restart).
- **A library that exits at import.** A library or variable file that calls `sys.exit()` at import ends only the loading process. Today the `SystemExit` reaches the analysing process: `robotcode analyze code` ends silently with that exit code, and the language server never finishes the task. The import now reports the exit code, as for a process that crashes (maintainer decision 2026-09-30).
- **Disk cache per argument set.** The disk cache keeps the documentation of a library or variable file per set of import arguments, resolved as RobotCode resolves them for the import today. An import whose arguments differ from a stored entry is loaded with its own arguments and reports its own errors; each argument set is cached on its own. A library that matches `ignore-arguments-for-library` keeps one entry (maintainer decision 2026-09-30).
- **Visible fallback without arguments.** If a library cannot be loaded with the import's arguments, RobotCode still tries to load it without arguments, as today. It then marks the result and reports on the import, together with the original error, that the keywords shown come from a load without arguments (maintainer decision: retry and report it). `doc-cli`, applied after this change, reads the same marker and aborts instead of documenting that load.

Not part of this change (maintainer decision 2026-09-29): asking a library for its keyword names before its documentation, and a warning for library imports that Robot Framework 7.4 and newer ignore.

## Capabilities

### New Capabilities

- `library-imports`: How RobotCode loads library and variable file imports for the analysis. This covers the time limit, the handling of a timed-out load, a library that exits at import, the disk cache per argument set, and the visible fallback without arguments.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/imports_manager.py`: `_run_in_subprocess` (terminate the worker on timeout); `_get_library_libdoc` and `_get_variables_libdoc` (a timeout becomes an error result that is not written to the disk cache; the disk cache key includes the import arguments); `LibraryMetaData` (the key per argument set) and `_save_import_cache`.
- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: a new `LibraryDoc` field, set by `get_library_doc` when the documented instance comes from the fallback without arguments. Must work on RF 5.0 to 7.5.
- `packages/robot/src/robotcode/robot/diagnostics/import_resolver.py`:
  - `_report_entry_errors`, for the fallback message;
  - `_import_default_libraries`, for the errors of a timed-out default library;
  - the dependency metas in `_import_library` and `_import_variables`, so that a timed-out import keeps the file out of the namespace cache.
- `packages/robot/src/robotcode/robot/diagnostics/errors.py`: one new diagnostic code. `docs/03_reference/analyzing-code.md`: documents the code and the timeout behaviour.
- Tests:
  - a hanging dummy library and variable file for the timeout;
  - a library whose arguments fail, with the fallback message.
- No change to the VS Code extension or the IntelliJ plugin.
