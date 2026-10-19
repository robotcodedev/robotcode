# Tasks

## 1. Language settings in the entries of Robot Framework files

- [x] 1.1 Move the computation of the fingerprint of the language settings out of `ImportsManager.__init__` into a function, and let `config_fingerprint` use it as before (design.md, "Store the fingerprint of the language settings with the doc"). Verify that the namespace cache tests pass unchanged: `tests/robotcode/robot/diagnostics/test_namespace_cache.py`, `tests/robotcode/language_server/robotframework/test_namespace_cache_restart.py` and `tests/robotcode/language_server/robotframework/parts/test_namespace_cache_restore.py`.
- [x] 1.2 Give `RobotFileMeta` the optional field `languages`. Let `_save_model_doc_cache` store the meta with the fingerprint, and let `_get_model_doc_cached` use a doc only when its meta equals the current meta with the fingerprint (design.md, "Store the fingerprint of the language settings with the doc"). Adjust the existing tests of `tests/robotcode/robot/diagnostics/test_resource_meta_binding.py` where they compare the stored meta. Verify with unit tests there:
  - an entry with the same file state and another fingerprint is not used;
  - an entry with the same file state and the same fingerprint is used;
  - `RobotFileMeta.from_document` and `get_resource_meta` keep `languages` empty, so their metas compare as before.

  Note (2026-10-19): the new tests are in the class `TestLanguageSettingsOfCachedDocs`. Of the existing tests, only `test_trusted_meta_saves_built_doc_under_that_meta` changed: it compared the saved meta by identity, now by equality. The analysis caches in the repository were cleared once, because the development version keeps its version number, so no entry without language settings is left.
- [x] 1.3 Add a test module in `tests/robotcode/analyze/code/` for the two scenarios of the requirement in `specs/namespace-cache/spec.md`. It runs `CodeAnalyzer` twice on a project in `tmp_path`, as `test_code_analyzer_cache_cleanup.py` does, with a robot profile without and with `languages = ["de"]`. The files are backdated, so that their entries are stored. Verify:
  - both scenarios pass;
  - both fail with tasks 1.1 and 1.2 reverted, as in the reproduction in proposal.md.

  Note (2026-10-19): the module is `test_code_analyzer_languages.py`; green on Robot Framework 7.5 and 6.0, skipped on 5.0, which has no language settings. With the doc cache's old lookup and saving put back by a pytest plugin outside the repository, both tests fail in their second run.

## 2. Integration

- [x] 2.1 Run `hatch run test:test` and `hatch run lint:all`. Verify that every Robot Framework environment is green, and that ruff and mypy report nothing.

  Note (2026-10-19): all nine environments green (Robot Framework 5.0: 5,033 passed, up to 7.5: 5,383 passed; no failures), 2,428 s; ruff and mypy without findings in 484 source files.
- [ ] 2.2 After the maintainer pushes, verify that the CI's Python tests are green on Linux, Windows and macOS.

## Workflow follow-up

- Archive the change after the maintainer's review, and sync its requirement into the main spec `namespace-cache`.
