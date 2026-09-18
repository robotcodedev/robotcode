# Proposal: deprecation-diagnostics

## Why

Robot Framework 7.5 deprecates several spellings without warning about them yet: the French test-cases header `Unités de test` (now `Cas de test`), the Finnish tag settings `Tagit`/`Testin Tagit`/`Tehtävän Tagit`/`Avainsanan Tagit` (now `Tunnisteet` …), and keyword documentation whose `Tags:` section is not preceded by an empty row (RF 7.5 warns on every execution of such a keyword and will stop recognising the tags later). Warnings for the translations are announced for RF 7.6, and the new spellings are hard errors on RF ≤ 7.4. Today RobotCode reports nothing for any of these, offers the deprecated Finnish settings in completion unmarked, and has no quick fix, so users only learn about the deprecations from Robot Framework's console output at run time, if at all.

## What Changes

- **Deprecated translations** (RF ≥ 7.5, from `Languages.deprecations`, so custom language files are covered too): every section header or setting written in a deprecated spelling gets an information-level diagnostic with the Deprecated tag ("… is deprecated since Robot Framework 7.5. Use 'Cas de test' instead."), a quick fix that replaces the term while keeping the header decoration (`*** … ***`) or brackets, and completion marks deprecated setting names as deprecated and sorts them last (deprecated headers are already not offered). Nothing is reported on RF ≤ 7.4, where the replacement would not lex.
- **`Tags:` without an empty row** in a keyword's `[Documentation]` in resource and suite files (RF ≥ 7.5, the case Robot Framework warns about): a warning with the Deprecated tag on the `Tags:` line and a quick fix that inserts an empty continuation row before it. Python library keywords have no in-file position and are out of scope.
- **Architecture**: one shared rule module used by both analyzers (the legacy `NamespaceAnalyzer` and the `SemanticAnalyzer`), so the diagnostics are identical regardless of the `semanticModel` flag and survive the planned removal of the legacy analyzer. New diagnostic codes are registered and documented, and can be suppressed with the existing modifiers (`# robotcode: ignore[...]`, `-mi`).
- **Tag-pattern spellings** (`FooANDbar` — an operator glued to a tag that is not all lower-case — and `a&b`): no new code — RF 7.5 already prints its own warnings through `robotcode robot`, `discover --diagnostics` and `results`; the documentation gets a note phrased like RF's rule (operators must be surrounded with spaces or tag names must be lower case; all-lower-case `fooANDbar` stays valid). Soft-deprecated `list_`/`time_` argument names have no runtime warning; RF's own docstring note in Collections is already shown in the rendered documentation, so RobotCode adds nothing.

Depends on `support-rf75` (`rf75` environment; the `parse_docstring` helper as the future place for a library-keyword note). Independent of the semantic-model changes as long as both analyzers are wired.

## Capabilities

### New Capabilities

- `deprecation-diagnostics`: Diagnostics, quick fixes and completion behaviour for spellings Robot Framework has deprecated — translated section headers and settings, and the layout of `Tags:` sections in keyword documentation — including their version gating and suppressibility.

### Modified Capabilities

<!-- none -->

## Impact

- New `packages/robot/src/robotcode/robot/diagnostics/deprecations.py` (rule functions and replacement computation); `errors.py` (new codes `DEPRECATED_TRANSLATION`, `TAGS_WITHOUT_EMPTY_ROW`); `utils/stubs.py` (`Languages.deprecations`).
- `packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py` and `semantic_analyzer/analyzer.py`: wiring in the section-header, tag-setting and documentation visitors.
- `packages/language_server/.../parts/code_action_quick_fixes.py`: two collect/resolve pairs; `parts/completion.py`: deprecated tag and sort key for setting items.
- Docs: `docs/03_reference/analyzing-code.md` (codes), `docs/03_reference/diagnostics-modifiers.md` (optional row), `docs/02_get_started/configuration.md` (languages note), `docs/03_reference/analyzing-results.md` and the `includes`/`excludes` option text (tag-pattern note).
- Tests: new `tests/robotcode/robot/diagnostics/test_deprecation_diagnostics.py` parametrised over both analyzers, quick-fix pure-function tests in `test_code_action_quick_fixes_model.py`, a completion unit test, a modifier opt-out test.
- No change to the VS Code extension or the IntelliJ plugin (diagnostic and completion tags are rendered by the LSP clients).
