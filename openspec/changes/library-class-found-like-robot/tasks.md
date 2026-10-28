# Tasks

## 1. The importer type (design D1–D3)

- [x] 1.1 In `_import_test_library` (`packages/robot/src/robotcode/robot/diagnostics/library_doc.py`), create the `Importer` with `"library"` instead of `"test library"` (D1). Change the expected text in `TestFailingLoads.test_unknown_library` (`tests/robotcode/repl/test_doc_cli.py`) to "Importing library 'NoSuchLib' failed" (D3).
- [x] 1.2 Add `TestLibraryClassLikeRobot` to `tests/robotcode/robot/diagnostics/test_library_loading.py`, loading through the spawned worker (`_load_library`) with libraries written to `tmp_path`, each with its own module name; for the import by name, put `tmp_path` on `sys.path` with `monkeypatch.syspath_prepend` (the spawned worker takes over `sys.path`):
  - RF ≥ 7.2: `mylib.keywords` from the issue by name gives `Do Greeting`, its source is `mylib/keywords.py` and its line the one of `def do_greeting`;
  - RF ≥ 7.2: an `@library` class of another name with an `@keyword` method, by path, gives that keyword;
  - RF < 7.2: `mylib.keywords` gives no keywords, as `robot` loads the module;
  - every version: a module with two classes with `ROBOT_AUTO_KEYWORDS` and no module-level keywords gives no keywords.

  The two RF ≥ 7.2 tests pass with the fix and fail without it. Verify with `hatch run test:test` and `hatch run lint:all`.

## 2. Check with the issue's example

- [x] 2.1 Run the example of issue #678 in the scratchpad (user configuration kept out with `XDG_CONFIG_HOME`, cache cleared) with `robotcode analyze code test.robot --pythonpath .` on `test.rf71` and `test.rf75`, before and after the change: on 7.5 `LibraryContainsNoKeywords` and `KeywordNotFound` are reported before and nothing after; on 7.1 both are reported before and after, as `robot --dryrun` fails there too. A `Library    NoSuchLib` reports "Importing library 'NoSuchLib' failed: …" after the change.

## Workflow follow-up

- Comment on issue #678 after the commit.
- Archive the change after review.
