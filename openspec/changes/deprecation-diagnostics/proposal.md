# Proposal: deprecation-diagnostics

## Why

Robot Framework 7.5 warns on every execution of a keyword whose `[Documentation]` has a `Tags:` section that is not preceded by an empty row (`[ WARN ] Invalid documentation in '<keyword>': Not having an empty row before 'Tags:' is deprecated.`), and Libdoc prints the same warning; the empty row becomes mandatory in Robot Framework 8 or 9. RobotCode reports nothing for such a keyword in the editor, although it parses the same documentation with Robot Framework's own parser (`support-rf75`) and merely swallows the warning, so users only learn about the deprecation from the console at run time.

Robot Framework 7.5 also renamed translated spellings — the French test-cases header `Unités de test` (now `Cas de test`) and the Finnish tag settings `Tagit`/`Testin Tagit`/… (now `Tunnisteet`/…) — but does not warn about them: `Languages.get_deprecation()` exists and is called by nothing, on 7.5 and on the current master, because warnings in the parsing model are still open (robotframework/robotframework#5210, milestone 7.6). Maintainer decision (2026-09-22): RobotCode reports deprecations only where Robot Framework itself warns, so the translations are left out of this change; revisit them when Robot Framework starts warning.

## What Changes

- **`Tags:` without an empty row** in the `[Documentation]` of a keyword in a `.resource` file or in the `*** Keywords ***` section of a `.robot` file (RF ≥ 7.5, the case Robot Framework warns about): a warning with the Deprecated tag on the `Tags:` line, shown while the file is edited. Python library keywords have no in-file position and are out of scope.
- **Both analysis paths**: one rule function in the existing `diagnostic_rules.py`, called from the documentation visitor of the legacy `NamespaceAnalyzer` and of the `SemanticAnalyzer` (the semantic-model path), so the diagnostic is identical regardless of the `semanticModel` flag and survives the removal of the legacy analyzer. The new diagnostic code is registered and documented, and can be suppressed with the existing modifiers (`# robotcode: ignore[...]`, `-mi`).
- **Left out** (maintainer decisions): a quick fix that inserts the empty row; any note on tag patterns (`FooANDbar`, `a&b`), for which Robot Framework 7.5 prints its own warnings; diagnostics, quick fix and completion marking for deprecated translated headers and settings (see Why).

Depends on `support-rf75` (`rf75` environment). Works with the semantic-model changes: until `semantic-model-switchover` both analyzers produce the diagnostic, after `semantic-model-cleanup` only the call in the `SemanticAnalyzer` remains.

## Capabilities

### New Capabilities

- `deprecation-diagnostics`: The diagnostic RobotCode provides for the layout of `Tags:` sections in keyword documentation that Robot Framework has deprecated, including its version gating and suppressibility.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/diagnostic_rules.py` (rule function); `errors.py` (new code `TAGS_WITHOUT_EMPTY_ROW`).
- `packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py` and `semantic_analyzer/analyzer.py`: wiring in the documentation visitor.
- Docs: `docs/03_reference/analyzing-code.md` (code), `docs/03_reference/diagnostics-modifiers.md` (optional row).
- Tests: new `tests/robotcode/robot/diagnostics/test_deprecation_diagnostics.py` (rule function and `SemanticAnalyzer`, a modifier opt-out test), a parity case in `test_variable_pipeline_comparison.py` for the `NamespaceAnalyzer`.
- No change to the VS Code extension or the IntelliJ plugin (diagnostic tags are rendered by the LSP clients).
