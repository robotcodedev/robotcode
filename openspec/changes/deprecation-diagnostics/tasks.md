# Tasks: deprecation-diagnostics

## 1. Rule function

- [x] 1.1 Add `tags_line_without_empty_row(doc: str) -> Optional[int]` to `packages/robot/src/robotcode/robot/diagnostics/diagnostic_rules.py` (Robot Framework's section-header expression and the "may a section start here" state: first line, after an empty line, inside a named `Args:`/`Returns:`/`Raises:` section), plus `tags_row_without_empty_row(documentation)` that applies it to the statement's `value` and returns the `ARGUMENT` tokens of the matching source row (a row ending with a backslash or `\n` continues on the next row), so both analyzers share the mapping and register `TAGS_WITHOUT_EMPTY_ROW` in `errors.py`; verify with tests in a new `tests/robotcode/robot/diagnostics/test_deprecation_diagnostics.py` for text then `Tags:` (index of the `Tags:` line), empty line before `Tags:`, `Tags:` first, `Tags:` after an `Args:` section with an indented entry, a prose line `tags: for grouping`, `**Tags:**`, `Tags::` and `_Tags_:` (all `None` except the reported cases)

## 2. Analyzers

- [x] 2.1 Call `tags_row_without_empty_row` in `visit_DocumentationOrMetadata` of `SemanticAnalyzer` and `NamespaceAnalyzer` for the `[Documentation]` of a keyword (node stack) under `RF_VERSION >= (7, 5)` and emit `TagsWithoutEmptyRow` (WARNING, Deprecated tag, RF's message "Invalid documentation in '<keyword>': Not having an empty row before 'Tags:' is deprecated."); verify with `analyzer_factory` tests in `test_deprecation_diagnostics.py` that a legacy layout in a `.resource` keyword and in a `.robot` keyword yields exactly one warning with the expected code, tag and range, that a `Tags:` row after a row continued with a backslash is found, that the correct layouts (empty row, first line, after `Args:`) yield none, that suite, test and resource-file documentation are not checked, that nothing is reported on RF < 7.5 (inverse gate), and that `# robotcode: ignore[TagsWithoutEmptyRow]` suppresses it through `DiagnosticsModifier`; add a `_PARITY_CASES` entry with the legacy and the correct layouts to `test_variable_pipeline_comparison.py`
- [x] 2.2 Run `hatch run test:test -- tests/robotcode/robot/diagnostics` and confirm the analyzer snapshot and pipeline-comparison tests are unchanged apart from the new case

## 3. Documentation and verification

- [x] 3.1 Add the code to the deprecation list in `docs/03_reference/analyzing-code.md` (not to the "common codes" table of `docs/03_reference/diagnostics-modifiers.md`, which lists only the most frequent codes); verify with `npm run docs:build`
- [x] 3.2 Run `hatch run lint:all` and `hatch run test:test` (full matrix incl. `rf75`) and confirm both pass; manually check in VS Code on RF 7.5 that the `Tags:` warning shows with strike-through, with and without the `semanticModel` flag
