# Tasks

## 1. Repeated resource import

- [ ] 1.1 Create `tests/robotcode/language_server/robotframework/parts/test_import_navigation.py`. It writes the import variants of the proposal's table into `tmp_path` and opens every Robot Framework file of that project with `open_temp_document`. For every import statement it checks the hover and Go to Definition:
  - the hover shows the target, and on a repeated import it is the same as on the first import;
  - Go to Definition opens the target, except on a second import in the same file, where it leads to the file (the first import), and on an import with an alias, which keeps its two targets (decision of 2026-10-07);
  - the "already imported" information stays.

  Verify that the tests for the repeated `Resource` imports fail on the current code and the others pass.
- [ ] 1.2 In `_import_resource` (`import_resolver.py`), register a repeated import in `import_entries`, as `_import_library` and `_import_variables` do:
  - an entry with the statement's range and file, and the already imported resource's documentation;
  - then report "already imported" and return without adding to `resources` and without following the resource's imports.

  Verify that the tests of 1.1 pass and that `hatch run test.rf75:test tests/robotcode/robot/diagnostics` stays green.

## 2. Find References on imports

- [ ] 2.1 Extend `test_import_navigation.py` with Find References on every import statement. Check that every import line of the same target in the temporary project appears exactly once, that no location appears twice, and that the result is the same from a repeated import as from the first import. Locations outside the temporary project are ignored. Verify that the doubled `Coll2` line and the missing direct import lines make these tests fail on the current code.
- [ ] 2.2 Add calls with a library or resource prefix to the project of `test_import_navigation.py`: `a.A Keyword` in two suites that import `a.resource`, next to the existing `Collections.` and `OperatingSystem.` calls. Check that Find References on every import of the target lists them. Verify that the call in the second suite is missing on the current code when the search starts in the first suite (decision of 2026-10-07).
- [ ] 2.3 In `references.py`:
  - `_find_library_import_references_in_file`, `_find_resource_import_references_in_file` and `_find_variables_import_references_in_file` read a file's import lines from its `import_entries`, matching the target as today.
  - The library and resource variants add the usages from `namespace_references` and skip locations already in the file's result. For libraries the usages are found as today; for resource files, every resource entry with the target's source counts.
  - `references_ResourceImport` finds the target through the statement's entry in `import_entries`.

  Verify that the tests of 2.1 and 2.2 pass and that `tests/robotcode/language_server/robotframework/parts/test_references.py` passes without changes to its regression outputs.
- [ ] 2.4 Switch `test_libraries_of_one_module.py` from comparing sets of lines to comparing lists, now that no line is doubled. Verify that it passes.

## 3. Integration

- [ ] 3.1 Run `hatch run test:test` and verify that every Robot Framework environment is green. If a regression output changes, review the difference before resetting it, and note it here.
- [ ] 3.2 Run `hatch run lint:all` and verify that ruff and mypy report nothing.
- [ ] 3.3 After the maintainer pushes, verify that the CI's Python tests are green on Linux, Windows and macOS.

## Workflow follow-up

- Archive the change after the maintainer's review; the archive creates the main spec `import-navigation`.
