# Tasks

## 1. Shared test setup

- [x] 1.1 Let `open_temp_document` in `tests/robotcode/language_server/robotframework/parts/conftest.py` switch the namespace disk cache off during each test (`monkeypatch` on `cache_namespaces`) and open documents without a version. Extend its docstring with both reasons. Verify that the modules using the fixture pass with the same numbers of passed and skipped tests as before: `test_completion_argument_docs`, `test_completion_builtin_variables`, `test_documentation_target`, `test_hover_documentation_links`, `test_hover_test_metadata`, `test_libraries_of_one_module`, `test_markdown_resource_imports` and `test_signature_help_documentation_links`, run with `hatch run test.rf75:test <files>`.

  Notes:
  - Since the plan, `test_import_navigation` (change `duplicate-import-navigation`) uses the fixture too. All nine modules gave the same counts before and after: 82 passed, 2 skipped.
  - The first implementation (fbc7ea5f) opened the documents with `version=1`. A matrix run on 2026-10-08 failed once on Robot Framework 7.4, because the background diagnostics analyzed closed test documents and put them back into the reference index (design.md, "Decisions").
  - Replaced on 2026-10-08 and checked again:
    - with the background analysis of test documents delayed by 0.8 s, `test_import_navigation` and `test_references` on Robot Framework 7.4 and 7.5 showed no background analysis of a test document and no file left in the index;
    - the nine modules still have 82 passed and 2 skipped.
- [x] 1.2 Add a helper to `tests/robotcode/language_server/robotframework/tools.py`. It takes a root directory and a dictionary of relative paths and texts, writes the files as UTF-8 (creating subdirectories), sets their access and modification time ten seconds into the past with `os.utime`, and returns the root. A comment gives the reason: import results of files younger than 2 s are not cached. Verify with `hatch run lint:all`, and through its use in group 2.

## 2. One project per module

- [x] 2.1 `test_hover_documentation_links.py`: make `project` a fixture with `scope="module"` that writes its files with the helper into `tmp_path_factory.mktemp("project")`. Its docstring says the project is shared by the module's tests and is read-only. Verify:
  - the module passes alone on Robot Framework 7.5 (24 passed);
  - a single test of it passes alone;
  - a throw-away pytest plugin outside the repository, which counts the calls of `ImportsManager._run_in_subprocess`, reports at most 28 for the module run alone (design.md, "Checked locally").
- [x] 2.2 `test_documentation_target.py`: the same change to its `project` fixture. Verify: 18 passed, a single test alone passes, and at most 27 import subprocesses when run alone.
- [x] 2.3 `test_signature_help_documentation_links.py`:
  - add a module-scoped `project` fixture that writes `arglib.py`, `faillib.py`, `sigvars.py` and `suite.robot` with the helper;
  - let the per-test `document` fixture keep its monkeypatches and open `project / "suite.robot"`;
  - compare `baseDir` with `project` instead of `tmp_path` in the tests.

  Verify: 7 passed and 1 skipped, a single test alone passes, and at most 32 import subprocesses when run alone.

## 3. Integration

- [x] 3.1 Run `hatch run test:test`. Verify that every Robot Framework environment is green, and that the Robot Framework 7.5 run takes clearly less than the 251 s of test time measured before (expected: about 190 s). Note the duration in this task.

  Note (2026-10-07):
  - All nine environments are green, with the same numbers of passed and skipped tests as in the run before this change, and no regression output changed.
  - Robot Framework 7.5 took 199.6 s, against 261.2 s in that run (5003 tests; the 251 s of the analysis were measured with 4989 tests).
  - The whole matrix took 1753 s of test time instead of 2181 s, about 7 minutes less.
  - After the replacement of the version (task 1.1), the matrix was green again in all nine environments on 2026-10-08, with 1887 s of test time; the run includes the tests of the other changes since then.
- [x] 3.2 Run `hatch run lint:all` and verify that ruff and mypy report nothing.
- [ ] 3.3 After the maintainer pushes, verify that the CI's Python tests are green on Linux, Windows and macOS.

## Workflow follow-up

- Archive the change after the maintainer's review. The change has no spec deltas, so no main spec is affected.
