# Proposal: deprecation-diagnostics

## Why

Robot Framework 7.5 warns on every execution of a keyword whose `[Documentation]` has a `Tags:` section that is not preceded by an empty row (`[ WARN ] Invalid documentation in '<keyword>': Not having an empty row before 'Tags:' is deprecated.`), and Libdoc prints the same warning; the empty row becomes mandatory in Robot Framework 8 or 9. RobotCode reports nothing for such a keyword in the editor, although it parses the same documentation with Robot Framework's own parser (`support-rf75`) and merely swallows the warning, so users only learn about the deprecation from the console at run time and have no quick fix.

Robot Framework 7.5 also renamed translated spellings — the French test-cases header `Unités de test` (now `Cas de test`) and the Finnish tag settings `Tagit`/`Testin Tagit`/… (now `Tunnisteet`/…) — but does not warn about them: `Languages.get_deprecation()` exists and is called by nothing, on 7.5 and on the current master, because warnings in the parsing model are still open (robotframework/robotframework#5210, milestone 7.6). Maintainer decision (2026-09-22): RobotCode reports deprecations only where Robot Framework itself warns, so the translations are left out of this change; revisit them when Robot Framework starts warning.

## What Changes

- **`Tags:` without an empty row** in a keyword's `[Documentation]` in resource and suite files (RF ≥ 7.5, the case Robot Framework warns about): a warning with the Deprecated tag on the `Tags:` line and a quick fix that inserts an empty continuation row before it. Python library keywords have no in-file position and are out of scope.
- **Architecture**: one rule module used by both analyzers (the legacy `NamespaceAnalyzer` and the `SemanticAnalyzer`), so the diagnostic is identical regardless of the `semanticModel` flag and survives the planned removal of the legacy analyzer. The new diagnostic code is registered and documented, and can be suppressed with the existing modifiers (`# robotcode: ignore[...]`, `-mi`).
- **Tag-pattern spellings** (`FooANDbar` — an operator glued to a tag that is not all lower-case — and `a&b`): no new code — RF 7.5 already prints its own warnings through `robotcode robot`, `discover --diagnostics` and `results`; the documentation gets a note phrased like RF's rule (operators must be surrounded with spaces or tag names must be lower case; all-lower-case `fooANDbar` stays valid). Soft-deprecated `list_`/`time_` argument names have no runtime warning; RF's own docstring note in Collections is already shown in the rendered documentation, so RobotCode adds nothing.
- **Dropped from the first version of this proposal**: diagnostics, quick fix and completion marking for deprecated translated headers and settings (see Why).

Depends on `support-rf75` (`rf75` environment; the `parse_docstring` helper as the future place for a library-keyword note). Independent of the semantic-model changes as long as both analyzers are wired.

## Capabilities

### New Capabilities

- `deprecation-diagnostics`: The diagnostic and quick fix RobotCode provides for the layout of `Tags:` sections in keyword documentation that Robot Framework has deprecated, including its version gating and suppressibility.

### Modified Capabilities

<!-- none -->

## Impact

- New `packages/robot/src/robotcode/robot/diagnostics/deprecations.py` (rule function); `errors.py` (new code `TAGS_WITHOUT_EMPTY_ROW`).
- `packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py` and `semantic_analyzer/analyzer.py`: wiring in the documentation visitor.
- `packages/language_server/.../parts/code_action_quick_fixes.py`: one collect/resolve pair.
- Docs: `docs/03_reference/analyzing-code.md` (code), `docs/03_reference/diagnostics-modifiers.md` (optional row), `docs/03_reference/analyzing-results.md` and the `includes`/`excludes` option text (tag-pattern note).
- Tests: new `tests/robotcode/robot/diagnostics/test_deprecation_diagnostics.py` parametrised over both analyzers, quick-fix pure-function tests in `test_code_action_quick_fixes_model.py`, a modifier opt-out test.
- No change to the VS Code extension or the IntelliJ plugin (diagnostic tags are rendered by the LSP clients).
