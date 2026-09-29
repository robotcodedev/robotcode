# Proposal: library-loading-robustness

## Why

Loading a library for the analysis can block far longer than `load-library-timeout`. `_run_in_subprocess` (`packages/robot/src/robotcode/robot/diagnostics/imports_manager.py:1641-1666`) raises its timeout error but then waits in `executor.shutdown(wait=True)` for the worker to finish. With a `Remote` library pointing at a host that drops packets, `robotcode analyze code` took 540 s although the timeout was set to 5 s. With a 1 s timeout and a library that sleeps 5 s, the call returned after 5.3 s. A timed-out load is not remembered either (`imports_manager.py:218-225`, `:284-297`), so every namespace build tries again and blocks again.

A smaller problem adds to this. If a library cannot be instantiated with the import's arguments, `get_library_doc` loads it again without arguments and serves those keywords (`packages/robot/src/robotcode/robot/diagnostics/library_doc.py:2513-2533`). The import only shows the original error (for example "Import definition contains errors."). Nothing says that the keywords shown come from a load without arguments.

These problems exist today, independent of any new feature. The parked `library-keyword-set-declaration` builds on the hard timeout, the kept `None` dependency meta (design D2) and the test setup of this change.

## What Changes

The change is limited to three points (maintainer decision 2026-09-29):

- **Hard timeout.** When `load-library-timeout` expires, the worker process that loads a library or variable file is terminated. The call returns after the timeout, not when the library gives up.
- **Remembered timeout.** A load that times out is kept as an error result in its import entry, as a refused `Remote` connection already is today. It is not retried on every namespace build. It is loaded again when the library's files or the configuration change, or when the language server restarts (for example with Clear Cache and Restart).
- **Visible fallback without arguments.** If a library cannot be loaded with the import's arguments, RobotCode still tries to load it without arguments, as today. It then marks the result and reports on the import, together with the original error, that the keywords shown come from a load without arguments (maintainer decision: retry and report it). `doc-cli`, applied after this change, reads the same marker and aborts instead of documenting that load.

Not part of this change (maintainer decision 2026-09-29): asking a library for its keyword names before its documentation, and a warning for library imports that Robot Framework 7.4 and newer ignore.

## Capabilities

### New Capabilities

- `library-imports`: How RobotCode loads library and variable file imports for the analysis. This covers the time limit, the handling of a timed-out load, and the visible fallback without arguments.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/imports_manager.py`: `_run_in_subprocess` (terminate the worker on timeout); `_get_library_libdoc` and `_get_variables_libdoc` (a timeout becomes an error result that is not written to the disk cache).
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
