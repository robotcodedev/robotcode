# Proposal

## Why

Since Robot Framework 7.2, a library module may hold its library class under another name than the module's, as long as it is the only class of that module marked with `ROBOT_AUTO_KEYWORDS` (set by `@library` or by hand). `robot` then uses that class, but RobotCode still loads the module, reports `LibraryContainsNoKeywords` on the import and `KeywordNotFound` for every keyword of the class, although the run passes (issue #678).

## What Changes

- RobotCode chooses the class or module of a library import as the installed Robot Framework does, so a library class whose name differs from its module is found on Robot Framework ≥ 7.2: its keywords, documentation and locations are available in the analysis, the language server and `robotcode doc`.
- On Robot Framework < 7.2 nothing changes; there, `robot` itself loads the module too.
- A failed library import reads "Importing library 'X' failed: …", as in `robot`'s own message, instead of "Importing test library 'X' failed: …".

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `library-imports`: adds the requirement that the class or module of a library import is chosen as Robot Framework chooses it, including a library class whose name differs from its module.

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: `_import_test_library`, which every library load goes through (analysis load worker, `robotcode doc`, the language server's documentation server).
- Tests: a new regression test for the library loading; the expected message in `tests/robotcode/repl/test_doc_cli.py`.
- Users who hit the problem need no action after the update: the stored library documentation belongs to the RobotCode version and is loaded again by the new one.
