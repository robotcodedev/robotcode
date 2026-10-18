# Tasks

## 1. Keep marks that arrive after an analysis

- [ ] 1.1 Give `DiagnosticsData` the counter of marks, count it up in `force_refresh_document` (also when `force` is already set), in `force_refresh_all` and in the marking of related documents. Let `run_workspace_diagnostics` note the diagnostics data object and the counter of each document it analyzes, and let `reset_document_diagnostics_data` clear `force` only when both are unchanged (design.md, "Keep a mark that arrives after the loop analyzed a file"). Verify with tests in a new module next to `tests/robotcode/language_server/robotframework/parts/test_invalidation_handlers.py`, which call the methods of the diagnostics part in the order of the race:
  - a document marked, noted as analyzed, marked again and then reset still needs an update;
  - a document marked, noted as analyzed and reset without a further mark no longer needs one;
  - a document whose diagnostics data was replaced after it was noted still needs an update after the reset;
  - the first and the third test fail with the change reverted.
- [ ] 1.2 Add a language-server test for the two scenarios of the requirement in `specs/workspace-references/spec.md`, started with `start_language_server` from `tools.py`. Several closed suites call `New Keyword`, which the resource file they import does not define yet:
  - the resource file is opened and `New Keyword` is added without saving; once the workspace analysis is done, Find References on it lists the calls in every suite;
  - `New Keyword` is added to the closed resource file on disk and the change is reported; once the workspace analysis is done, the same holds.

  The race does not show reliably in a test; task 1.1 covers it deterministically.
- [ ] 1.3 Check with the measurement script (design.md, "Measurement method") without the reuse of docs. Verify, and note the result in this task:
  - in 5 runs with an edit every 0.2 s, every suite uses the doc of the resource file's current text at the end;
  - in 5 runs with each edit analyzed to the end and each namespace handler of `resources_changed` delayed by 2 ms, no run waits in vain for a suite.

## 2. Keep the doc of unchanged files

- [ ] 2.1 In `ImportsManager`, keep the doc per normalized path with its `RobotFileMeta` in `_get_model_doc_cached` and `_save_model_doc_cache`, and empty the dict in `clear_cache` (design.md, "Keep the doc per file and disk state in the imports manager"). Give `_bind_get_libdoc_from_model` in `tests/robotcode/robot/diagnostics/test_resource_meta_binding.py` the new attribute. Verify with unit tests there:
  - a second lookup with an equal meta returns the same doc and does not read the disk cache;
  - a lookup with another modification time or size reads the disk cache;
  - a doc that `_save_model_doc_cache` stored is returned by the next lookup;
  - after `clear_cache`, a lookup reads the disk cache again;
  - the existing tests of the module still pass.
- [ ] 2.2 Add the `ImportsManager` method that removes the `RESOURCE` entries of files from the disk cache and from the dict. Use it in `remove_cached_analysis` and `remove_cached_analyses_of_missing_files` of `document_cache_helper.py` (design.md, "Drop the kept doc of a deleted file with its cache entries"). Verify:
  - a unit test: after the removal, a lookup of the file reads the disk cache again;
  - `tests/robotcode/language_server/robotframework/test_deleted_files.py` and `tests/robotcode/analyze/code/test_code_analyzer_cache_cleanup.py` pass.
- [ ] 2.3 Add a language-server test with a closed suite that imports a resource file, started with `start_language_server` from `tools.py`. The files are backdated, so that their states are trusted. Verify each case:
  - **the resource file changes on disk:** the suite's next namespace has the same own doc as before, and it resolves a keyword that the change added to the resource file;
  - **the resource file changes in the editor without being saved:** the suite's next namespace resolves the keyword added in the editor;
  - **the suite changes on disk:** its next namespace has a new own doc with the keyword the change added.

  The first case fails on its "same own doc" check with tasks 2.1 and 2.2 reverted; the other checks pass both with and without them.

## 3. Literal values without a cycle

- [ ] 3.1 Replace the inner function `_collect` of `ArgumentInfo._extract_literal_values` in `library_doc.py` with a static method that calls itself (design.md, "`_extract_literal_values` without a recursive inner function"). Verify with a unit test for Robot Framework 7.0 and later:
  - for a `Literal` inside a nested union, the values come in the order of the type hint;
  - with the garbage collector disabled, `gc.collect()` after a call finds nothing to free;
  - the test fails on the second check with the old inner function.

## 4. Integration

- [ ] 4.1 Measure as in design.md, "Measurement method", with both edit patterns, the current code and this change alternating, and record the figures in design.md next to those of the prototype. Verify:
  - in 5 runs of each pattern, every suite uses the doc of the resource file's current text, after each edit or at the end;
  - no suite doc and no `_collect` function is left in the garbage;
  - the garbage, the time of the collections and the CPU time are in the range of the prototype;
  - the resident set size of the process after the edits is not above that of the current code.
- [ ] 4.2 Run `hatch run test:test` and `hatch run lint:all`. Verify that every Robot Framework environment is green, and that ruff and mypy report nothing.
- [ ] 4.3 After the maintainer pushes, verify that the CI's Python tests are green on Linux, Windows and macOS.

## Workflow follow-up

- Archive the change after the maintainer's review, and sync its requirement into the main spec `workspace-references`.
