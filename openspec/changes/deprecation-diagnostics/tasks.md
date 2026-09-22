# Tasks: deprecation-diagnostics

## 1. Prerequisites and rule module

- [ ] 1.1 Confirm `support-rf75` is applied (`rf75` env exists); create `packages/robot/src/robotcode/robot/diagnostics/deprecations.py` with the pure function `find_tags_line_without_empty_row(documentation_node)` (RF's `header_re` and `can_start` rule over the rows of a `[Documentation]`, returning the `Tags:` row's token or `None`) and register `TAGS_WITHOUT_EMPTY_ROW` in `errors.py`; verify with pure-function tests in a new `tests/robotcode/robot/diagnostics/test_deprecation_diagnostics.py` (`Tags:`/`Tags::`/`**Tags:**`/`tags:` headers, `Tags:` as the first documentation row not reported, empty row before `Tags:` not reported, a prose row `Tags: …` after text reported like RF does)

## 2. Analyzer wiring

- [ ] 2.1 Wire the rule into `NamespaceAnalyzer` and `SemanticAnalyzer` (`visit_DocumentationOrMetadata` for keyword documentation via the node stack), emitting `TagsWithoutEmptyRow` (WARNING, Deprecated tag, message "Not having an empty row before 'Tags:' is deprecated.") under `RF_VERSION >= (7, 5)`; verify with tests in `test_deprecation_diagnostics.py` parametrised over both analyzers (extend `analyzer_factory` in `tests/robotcode/conftest.py` with an `analyzer_cls` parameter, following `_prepare_analyzer` in `test_variable_pipeline_comparison.py`) that a legacy `Tags:` layout in a resource keyword and in a suite-file keyword yields exactly one warning with the expected code, tag and range on the `Tags:` row, that the correct layout and `Tags:` as the first row yield none, that suite, test and resource-file documentation are not checked, that nothing is reported on RF < 7.5 (inverse gate), and that `# robotcode: ignore[TagsWithoutEmptyRow]` suppresses the diagnostic through `DiagnosticsModifier`
- [ ] 2.2 Run `hatch run test:test -- tests/robotcode/robot/diagnostics` and confirm the analyzer snapshot and pipeline-comparison tests are unchanged

## 3. Language server

- [ ] 3.1 Add `code_action_insert_empty_row_before_tags` / `resolve_…` to `packages/language_server/.../parts/code_action_quick_fixes.py` following the collect/resolve pattern, inserting `' ' * continuation_col + '...' + line ending` before the `Tags:` row; verify by extending `tests/robotcode/language_server/robotframework/parts/test_code_action_quick_fixes_model.py` with a pure-function test for the edit (indentation from the CONTINUATION token, e.g. column 4 → `    ...`) and a resolve test in the existing `object.__new__` + mock style

## 4. Documentation and verification

- [ ] 4.1 Add the code to the deprecation list in `docs/03_reference/analyzing-code.md` (and a row in `docs/03_reference/diagnostics-modifiers.md` if the common-codes table is kept), add a sentence to `docs/03_reference/analyzing-results.md` and a comment line to the `--include`/`--exclude` entries of the generator's `TOML_EXAMPLES` (`# RF 7.5: operators must be surrounded with spaces or tag names be lower case; '&' is deprecated`) that RF 7.5 warns about `a&b` and `FooANDbar` and RF 8 will change them, then regenerate `model.py`, `docs/public/schemas/robot.toml.json` and `docs/03_reference/config.md` with the sequence `CONTRIBUTING.md` documents; verify with `npm run docs:build` and that the regeneration sequence reproduces the three committed files with no diff
- [ ] 4.2 Run `hatch run lint:all` and `hatch run test:test` (full matrix incl. `rf75`) and confirm both pass; manually check in VS Code on RF 7.5 that the `Tags:` warning shows with strike-through and the quick fix inserts the row
