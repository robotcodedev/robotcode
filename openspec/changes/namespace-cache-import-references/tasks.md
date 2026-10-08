# Tasks

## 1. Restored references to imports

- [x] 1.1 Create `tests/robotcode/language_server/robotframework/parts/test_namespace_cache_restore.py` with the five cases of the proposal, as described in design.md ("Tests"). It opens each suite without a version, closes it, opens it again from the cache (checked with a spy on `Namespace.from_data`), and compares the entries and locations of `namespace_references`. Verify that the test fails for the five cases on the current code.
- [x] 1.2 Add a test to `tests/robotcode/robot/diagnostics/test_namespace_data.py`: two entries of the same library with different import positions get different keys in `to_data`. Adjust the comment on the key format in `test_to_data_converts_namespace_references`. Verify that the new test fails on the current code.
- [x] 1.3 In `namespace.py`, build the key of a `namespace_references` entry with one function used by `to_data` and `from_data`, from the fields named in design.md. In `from_data`, look the keys up among the entries of `libraries`, `resources`, `variables_imports` and `import_entries`. Verify that the tests of 1.1 and 1.2 pass and that `test_namespace_data.py` stays green.

## 2. Integration

- [x] 2.1 Run `hatch run test:test` and verify that every Robot Framework environment is green.

  Note (2026-10-08):
  - The first run failed once on Robot Framework 7.4 in `test_references`, because of a leak between tests from the change `doc-link-tests-per-module`, not from this change.
  - After that leak was fixed, all nine environments were green; Robot Framework 7.5 had 5014 passed and 95 skipped.
- [x] 2.2 Run `hatch run lint:all` and verify that ruff and mypy report nothing.
- [ ] 2.3 After the maintainer pushes, verify that the CI's Python tests are green on Linux, Windows and macOS.

  Note (2026-10-08): the first CI run (37783553021) failed on Windows in the 10 restore cases and in `test_an_unchanged_namespace_is_restored`, in every Windows job. The tests compared the source of the restored namespace with `str(suite)`. On Windows, `Uri.to_path()` gives that source a lower-case drive letter, so the string comparison never matched; both tests now compare paths. The run was cancelled; the next run decides this task.

## Workflow follow-up

- Archive the change after the maintainer's review; the archive creates the main spec `namespace-cache`.
