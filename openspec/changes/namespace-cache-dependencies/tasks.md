# Tasks

## 1. Restart tests

- [ ] 1.1 Create `tests/robotcode/language_server/robotframework/test_namespace_cache_restart.py` with the three scenarios of the spec, as described in design.md ("Tests"):
  - the top `vars.py` changed;
  - the top `helper.py` changed;
  - nothing changed, resource file first.

  Each test runs two language-server sessions on its own `tmp_path` workspace and checks with a spy on `Namespace.from_data` whether the suite was restored, and which variables or keywords the suite reports as not found. Verify that all three tests fail on the current code: the first two report nothing for the removed name, and the third is not restored.

## 2. Recording

- [ ] 2.1 Add a test, next to the resolver tests of `tests/robotcode/robot/diagnostics/test_library_loading.py` or in a module of its own: resolving a suite that imports `vars.py` and a resource file in `sub/` that imports `sub/vars.py` records two `var:` dependencies, under the absolute paths of both files. Do the same for two library files `helper.py`. Verify that it fails on the current code.
- [ ] 2.2 In `import_resolver.py`, record a library and a variable file under `lib:<cache_key>` and `var:<cache_key>` of their meta, also for the default libraries. Without a meta, or when the meta has no cache key, keep `lib:<import name>` and `var:<import name>`. Change the key `lib:BuiltIn` in `test_library_loading.py` to the new key. Verify that the test of 2.1 and `test_library_loading.py` pass.

## 3. Checking

- [ ] 3.1 Add unit tests to `tests/robotcode/robot/diagnostics/test_namespace_cache.py`:
  - two `var:` dependencies with different keys are each checked against their own file;
  - a loaded meta is looked up by cache key;
  - without a loaded meta, the meta is computed from the key, and not relative to the suite's folder.

  Verify that the new tests fail on the current code.
- [ ] 3.2 In `imports_manager.py`, let `get_cached_library_meta` and `get_cached_variables_meta` match a loaded file by the cache key of its meta. Let `validate_namespace_meta` look a `lib:` or `var:` dependency up by its key, and compute a missing meta with `get_library_meta(<key>)` or `get_variables_meta(<key>)`. Verify:
  - the tests of 3.1 and the whole of `test_namespace_cache.py` pass;
  - the restart tests of 1.1 pass.

## 4. Restore test

- [ ] 4.1 Let `tests/robotcode/language_server/robotframework/parts/test_namespace_cache_restore.py` (change `namespace-cache-import-references`) use the plain file names `vars.py` and `arglib.py` again, and remove its `unique()` helper and its comment. Verify that all ten cases pass, so the second analysis mode is restored from the cache although the first one loaded files with the same names from other folders.

## 5. Integration

- [ ] 5.1 Run `hatch run test:test` and verify that every Robot Framework environment is green.
- [ ] 5.2 Run `hatch run lint:all` and verify that ruff and mypy report nothing.
- [ ] 5.3 After the maintainer pushes, verify that the CI's Python tests are green on Linux, Windows and macOS.

## Workflow follow-up

- Archive this change after `namespace-cache-import-references`, which introduces the capability `namespace-cache`, and after the maintainer's review.
