# Design: library-class-found-like-robot

## Context

See proposal.md - Why. On `main`:

- Every library load goes through `_import_test_library` in `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`, called by `get_library_doc`: the analysis load worker (`ImportsManager._run_in_subprocess`), `robotcode doc` (`doc_cli.py`) and the language server's documentation server (`http_server.py`). It creates `Importer("test library", LOGGER)` and calls `import_class_or_module(name, return_source=True)`. The line has read so since the packages were split in 2023.
- Robot Framework's `Importer` decides with its `type` whether it looks for a library class: `library_import = type and type.upper() == "LIBRARY"` (RF 7.2–7.5 `robot/utils/importer.py`). Only then does `_get_possible_class` fall back to `_get_decorated_library_class_in_imported_module`, which takes the one class of the module that has the attribute `ROBOT_AUTO_KEYWORDS` and whose `__module__` is the module, and keeps the module when there is no such class or more than one. A class named like the module is still taken first. `@library` sets `ROBOT_AUTO_KEYWORDS` (to `False` by default).
- Robot Framework itself creates `Importer("library", logger=…)` in `robot/running/testlibraries.py` on every supported version (5.0–7.5). Up to RF 7.1 the `Importer` has no class lookup, and its `type` only names the import in its messages: "Importing {type} '{name}' failed: …", "Imported {type} …".
- Verified with `Importer(t).import_class_or_module(…)` on RF 7.1.1, 7.2.2 and 7.5, `t` being `"library"` and `"test library"`:
  - a module with one `@library` class of another name: the class with `"library"` on 7.2.2 and 7.5, the module otherwise;
  - two classes with `ROBOT_AUTO_KEYWORDS`, a marked class imported from another module, a plain class of another name: the module everywhere;
  - a class named like the module: the class everywhere.
- Reproduced issue #678 with its example: `robot --dryrun` passes on 7.2.2 and 7.5 and fails on 7.1.1 ("contains no keywords"); `robotcode analyze code` reports `LibraryContainsNoKeywords` and `KeywordNotFound` on all three. With `"library"` patched into `Importer` (scratchpad, not in the repo), `get_library_doc` on RF 7.5 returns `Do Greeting` without errors, with the library on the line of the class and the keyword on the line of `def do_greeting`. The same holds for the import by path and for an `@library` class with an `@keyword` method imported by path.
- `robotcode analyze code` reports a missing library as "Importing test library 'NoSuchLib' failed: …", `robot` as "Importing library 'NoSuchLib' failed: …".

## Goals / Non-Goals

**Goals:**

- The same class or module as `robot` for every library import, on every supported Robot Framework version.

**Non-Goals:**

- Own rules for finding a library class beyond Robot Framework's.
- Variable files (`Importer("variable file", …)`), which Robot Framework imports with the same type.

## Decisions

### D1: The importer gets Robot Framework's type `"library"`

`_import_test_library` creates `Importer("library", LOGGER)`, as Robot Framework does. Robot Framework then applies its own lookup on the versions that have it, and later changes of the lookup reach RobotCode without work on our side.

- **Alternative:** our own lookup of a marked class after the import. It duplicates Robot Framework's rule and has to follow its changes; rejected.

### D2: No version check

The type is passed on every Robot Framework version. Before 7.2 it only changes the wording of the importer's messages, which then match `robot`'s.

### D3: The wording of import errors follows

"Importing test library 'X' failed" becomes "Importing library 'X' failed" in the analysis, the language server and `robotcode doc`. No code of RobotCode reads that text; only the assertion in `tests/robotcode/repl/test_doc_cli.py` (`TestFailingLoads.test_unknown_library`) expects it. The strings in `tests/robotcode/analyze/code/test_print_diagnostics.py` are test input for the printing of long messages and stay.

## Risks / Trade-offs

- [A project relies on RobotCode loading the module where `robot` loads the class] → Not intended behavior: `robot` runs the class, so the analysis showed keywords that do not exist at run time.
- [Stored documentation from the old load] → The stored library documentation belongs to the RobotCode version (`DefaultDataCache`, `app_version`) and is dropped by the update. In a development checkout the cache has to be cleared once.
- [The open change `library-keyword-set-declaration` reads an attribute from the object `_import_test_library` returns] → It then gets the class `robot` uses, as intended there.
