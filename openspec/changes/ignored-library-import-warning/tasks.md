# Tasks

## 1. Test module

- [ ] 1.1 Create `tests/robotcode/language_server/robotframework/parts/test_ignored_library_imports.py`:
  - one project for the module, written once with `write_project` from `tools.py` as in the doc-link modules, with `helper.py`, `arglib.py`, a `broken.py` that raises at import, and the resource files and suites of the spec's scenarios;
  - documents opened with `open_temp_document`, in both analysis modes (legacy and semantic model), as in `test_import_navigation.py`;
  - a helper that returns the `LibraryImportIgnored` diagnostics of a document with line, message and related locations.

  Add the scenarios of the requirement "No warning where Robot Framework does not warn". The Robot Framework 7.3 scenario is covered by the version check of every test: on Robot Framework 7.3 and older, every test expects no `LibraryImportIgnored`. Verify with `hatch run test.rf75:test <module>` that these tests pass on the current code.

## 2. The analyzed file's own imports

- [ ] 2.1 Add a test for each scenario of the requirements "An import of another library under a used name is reported" and "An import of a library with other arguments under a used name is reported". On Robot Framework 7.4 and newer they expect the warning, its message and the related location of the earlier import; before 7.4 they expect none. Verify that the tests expecting a warning fail on Robot Framework 7.5 with the current code.
- [ ] 2.2 Implement the warning as described in design.md:
  - add `LIBRARY_IMPORT_IGNORED = "LibraryImportIgnored"` to `errors.py`;
  - in `import_resolver.py`, keep the resolved arguments of each registered entry, including the default libraries;
  - in `_import_library`, where the key is taken and no duplicate was found, report the warning on Robot Framework 7.4 and newer, distinguishing another library from other arguments, only when neither `LibraryDoc` has `errors`.

  Verify that the module of 1.1 passes on Robot Framework 7.5 and 7.3 (`hatch run test.rf75:test <module>`, `hatch run test.rf73:test <module>`).
- [ ] 2.3 Add `LibraryImportIgnored` to the import diagnostics in `docs/src/content/docs/guides/analyzing-code.md`, as a warning on Robot Framework 7.4 and newer for a library import that Robot Framework ignores because an earlier import uses its name. Verify that `npm run docs:build` succeeds.

## 3. Imports from resource files

- [ ] 3.1 Add a test for each scenario of the requirement "An ignored import in a resource file is reported at the Resource import". For the scenario with both imports in `common.resource`, check the analysis of `common.resource` and of both suites. Verify that the tests expecting a warning at a `Resource` import fail on Robot Framework 7.5 with the current code.
- [ ] 3.2 Pass `parent_import` from `_dispatch_import` to `_import_library`. For an import with `top_level=False`, report the warning at the range of the analyzed file's `Resource` statement, naming the ignored library and its resource file, with related locations of the ignored and the earlier import, as described in design.md. Verify:
  - the module passes on Robot Framework 7.5 and 7.3;
  - `robotcode analyze code` on a scratch project with the scenario "Name used by the suite" shows the warning at the suite's `Resource` line, with the location in `r.resource`.

## 4. Integration

- [ ] 4.1 Run `hatch run test:test` and verify that every Robot Framework environment is green. If regression outputs change, review each change before resetting it with `hatch run test:test-reset <ids>`.
- [ ] 4.2 Run `hatch run lint:all` and verify that ruff and mypy report nothing.
- [ ] 4.3 After the maintainer pushes, verify that the CI's Python tests are green on Linux, Windows and macOS.

## Workflow follow-up

- Archive the change after the maintainer's review; the archive creates the main spec `ignored-library-imports`.
