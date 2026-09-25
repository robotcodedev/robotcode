# Proposal: library-loading-robustness

## Why

Loading a library for the analysis can block far longer than `load-library-timeout`. `_run_in_subprocess` raises its timeout error but then waits in `executor.shutdown(wait=True)` for the worker to finish. With a `Remote` library pointing at a host that drops packets, `robotcode analyze code` took 540 s although the timeout was set to 5 s. A timed-out load is not remembered either, so every namespace build tries again and blocks again.

Three smaller problems add to this:
- A failed `Remote` load contacts the server twice as often as Robot Framework does. RobotCode asks for the introduction and importing documentation before the keyword names, and each of these requests connects again.
- If a library cannot be instantiated with the import's arguments, `get_library_doc` loads it again without arguments and serves those keywords. The import only shows the original error ("Import definition contains errors."). Nothing says that the keywords shown come from a load without arguments.
- A second import may use an already taken library name, either with different arguments or for another library. RobotCode drops that import without any diagnostic. Robot Framework 7.4 and newer warn in this case and ignore the import.

These problems exist today, independent of any new feature. `library-keyword-set-declaration` loads libraries once per set of import arguments and depends on the time limit holding.

## What Changes

- **Hard timeout.** When `load-library-timeout` expires, the worker process that loads a library or variable file is terminated. The call returns after the timeout, not when the library gives up.
- **Remembered failures.** A load that times out is kept as an error result in its import entry, as a refused `Remote` connection already is today. It is not retried on every namespace build. It is loaded again when the library's files or the configuration change, or when the language server restarts (for example with Clear Cache and Restart).
- **Keyword names first.** RobotCode asks a library for its keyword names before its introduction and importing documentation. If that call fails, it skips the documentation requests. For `Remote` this halves the connection attempts, as in Robot Framework.
- **Visible fallback without arguments.** If a library cannot be loaded with the import's arguments, RobotCode still tries to load it without arguments, as today (maintainer decision). It then reports on the import, together with the original error, that the keywords shown come from a load without arguments.
- **Duplicate import diagnostic.** On Robot Framework 7.4 and newer, RobotCode reports a warning on a library import that Robot Framework ignores. Robot Framework warns that the suite has already imported that library with different arguments, or another library with that name. The arguments are compared after static resolution. If a variable whose value is only known at runtime remains, no warning is reported. Built-in variables that Robot Framework only sets during the run, such as `${OUTPUT DIR}` or `${SUITE NAME}`, are known but have no value in this resolution, so an argument that refers to one gets no warning either (maintainer decision). Loading such a library does not change. The diagnostic goes on imports of the analysed file, like the existing `LibraryAlreadyImported` information. Conflicts that only arise through imported resource files are not reported. Older versions log the case only at INFO level, and RobotCode reports nothing there.
- **Open** (not decided):
  - **Duplicate loads without arguments.** Signature help, inlay hints and (with `semantic-model` enabled) the semantic analyzer start a separate load with `()` whenever the documentation of an import with arguments has errors. For libraries, the loader has already made that attempt. Should they use the loader's result instead? Variable files have no fallback in the loader, so for them these reloads are the only attempt without arguments.
  - **Processes the library started itself.** Should terminating the worker also end them? Examples are Java started by SikuliLibrary in its default mode, and node for Browser with `jsextension=`. This includes how it would work on Windows.
  - **Failed variable-file loads.** Today they are written to the disk cache and reused in later sessions. Should they be treated like libraries, whose failed results are not reused?
  - **Import-name completion.** It uses a shared worker with the same timeout-without-termination behaviour. Is it part of this change?
  - **A user-triggered retry** before files change or the server restarts. See the proposed "Reload library" action in `library-keyword-set-declaration`.

## Capabilities

### New Capabilities

- `library-imports`: How RobotCode loads and resolves library and variable file imports for the analysis. This covers the time limit, the handling of failed loads, the visible fallback without arguments, which calls are made to a library whose load failed, and the diagnostic for library imports that Robot Framework ignores.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/imports_manager.py`: `_run_in_subprocess` (terminate the worker on timeout); the failure handling of `_LibrariesEntry` / `_get_library_libdoc` and of the variable file equivalent; a method for the static resolution of import arguments, used by the duplicate check (the entry keys keep `resolve_args`).
- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: `get_library_doc_from_library` (order of the calls, skip after a keyword-name failure); `get_library_doc` (mark a result that comes from the fallback without arguments); the runtime-only built-ins of `_get_default_variables`, which the static resolution of import arguments leaves without a value. Must work on RF 5.0 to 7.5.
- `packages/robot/src/robotcode/robot/diagnostics/import_resolver.py`:
  - the dedup branch that drops the import today;
  - `_report_entry_errors`, for the fallback message;
  - `_import_default_libraries`, for the errors of a timed-out default library;
  - the dependency metas, so that a timed-out import keeps the file out of the namespace cache.
- `packages/robot/src/robotcode/robot/diagnostics/errors.py`: new diagnostic codes. `docs/03_reference/analyzing-code.md`: documents the codes.
- Depending on the open question: the reloads with `()` in `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py` and in `packages/language_server/src/robotcode/language_server/robotframework/parts/signature_help.py` / `inlay_hint.py`.
- Tests:
  - a hanging dummy library for the timeout;
  - a local `Remote` test server for the connection count;
  - a library whose arguments fail, with the fallback message;
  - the duplicate-import diagnostic on RF 7.4/7.5 (including arguments that resolve to the same value and arguments with a runtime-only built-in) and its absence on older versions.
- No change to the VS Code extension or the IntelliJ plugin.
