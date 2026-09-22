# Design: deprecation-diagnostics

## Context

See proposal.md. Verified facts:

- **RF 7.5.** `docstringparser` recognises section headers with `[*_]*(args|…|tags)[*_]*::?[*_]*` (case-insensitive, `fullmatch` on the stripped line) and warns "Not having an empty row before 'Tags:' is deprecated." when a `tags` header follows a non-empty line (`_match_header`, with a `TODO` to require the empty row in RF 8 or 9); `KeywordImplementation.all_tags` runs that parser on every execution of a keyword whose documentation contains a `Tags:` header, so the warning repeats at run time, and Libdoc's `update_docs` prints it once per keyword. A `[Documentation]` value joins one entry per source row with `\n`; an empty continuation row yields an empty line, and the `Tags:` row's `CONTINUATION` token gives the indentation for an inserted row. Tag-pattern deprecations (`&`, operator-adjacent mixed-case operands) are reported by RF itself wherever patterns are applied, which `robotcode robot`, `discover --diagnostics` and `results` already surface; `list_`/`time_` are documentation-only. Deprecated translations: `Languages.deprecations` maps the old terms to the new ones and to the English names, which is why they lex without a token error; `get_deprecation()` has no caller on 7.5 or on master (7.5.1.dev1), and a French/Finnish file with the old terms runs without any warning — the warning waits for robotframework/robotframework#5210 (warnings in the parsing model, milestone 7.6).
- **RobotCode.** Deprecation diagnostics exist as copy-pasted code in both analyzers (`DEPRECATED_FORCE_TAG` information, `DEPRECATED_HYPHEN_TAG` warning only where RF warns, `DEPRECATED_HEADER` from RF's token error, `DEPRECATED_RETURN_SETTING`), each with `DiagnosticTag.DEPRECATED`; every diagnostic passes the modifiers, so a new code is suppressible automatically. The `semanticModel` flag defaults to off, `Namespace` picks the analyzer by flag, and `dev-docs/semantic-model.md` requires identical output under both flags until the legacy analyzer is deleted; `diagnostic_rules.py` is the precedent for analyzer-independent rule code. `get_docstring_info` in `library_doc.py` (`support-rf75`) calls `parse_docstring` under `LOGGER.cache_only`, so RF's warning is produced and discarded. Quick fixes follow a collect/resolve pattern keyed by diagnostic code. Observed on RF 7.5: a keyword with the legacy `Tags:` layout yields zero RobotCode diagnostics.
- **Tests.** No analyzer test covers a `DEPRECATED_*` code; the analyzer test helper `analyzer_factory` builds a `SemanticAnalyzer`; quick-fix pure-function tests and resolve tests exist in `test_code_action_quick_fixes_model.py`.

## Goals / Non-Goals

**Goals:**
- Show the deprecation Robot Framework warns about where the user can act, with a one-click fix.
- Identical behaviour under both analysis paths; the rule survives the legacy analyzer's removal.

**Non-Goals:**
- Deprecated translated headers and settings (`Unités de test`, `Tagit`, …): Robot Framework does not warn about them yet (maintainer decision: RobotCode reports deprecations only where RF warns); revisit when RF does, then with RF's `get_deprecation()` wording and a check that RF's own token warning is not duplicated.
- Diagnostics for Python library keywords with a legacy `Tags:` layout (no in-file position; a hover note could build on `support-rf75`'s helper later).
- Re-implementing RF's tag-pattern grammar (`config check`, model validators, CLI pre-checks) — RF 7.5 already warns at every RobotCode touch point, RF 8 will change the grammar anyway.
- A hint for `list_=`/`time_=` named arguments (documentation-only deprecation without a runtime warning; RF's own note in the Collections docstrings is already part of the rendered documentation after `support-rf75`, BuiltIn's `Sleep`/`Get Time` carry no such note).

## Decisions

### D1: Rule module wired into both analyzers

`packages/robot/src/robotcode/robot/diagnostics/deprecations.py` holds a pure function `find_tags_line_without_empty_row(documentation_node)` reproducing RF's `header_re` and `can_start` rule over the source rows of a `[Documentation]` statement and returning the `Tags:` row's token. Both analyzers add a few lines in `visit_DocumentationOrMetadata` (keyword context via the node stack), calling the helper and `_append_diagnostics`. Inline duplication (the existing pattern) was rejected as the maintenance hazard `semantic-model-cleanup` names; a post-pass visitor in `Namespace` was rejected because it would bypass `AnalyzerResult`, the snapshot harness and the "single producer" rule. Module-scope `RF_VERSION >= (7, 5)` gating. Re-using `get_docstring_info`'s `parse_docstring` call and catching RF's logged warning was rejected: it runs on the joined documentation text without row positions, and the diagnostic needs the row.

### D2: Code, severity and wording

`TagsWithoutEmptyRow`, WARNING with the Deprecated tag — RF warns on every execution. The message is RF's, without its keyword prefix (the diagnostic already sits in the keyword): "Not having an empty row before 'Tags:' is deprecated."

### D3: Quick fix inserts a row

`code_action_insert_empty_row_before_tags` filters diagnostics by code and, on resolve, inserts `' ' * continuation_col + '...' + line ending` at the start of the `Tags:` row (no `Diagnostic.data`, no cache-format change). The indentation comes from the row's `CONTINUATION` token. The fix is safe on every Robot Framework version: before 7.5 the tags are taken from the last documentation line regardless of empty rows.

### D4: Gating and tests

Only on RF ≥ 7.5 (as `DEPRECATED_HYPHEN_TAG`: only where RF itself warns). Tests: a new analyzer test module parametrised over `NamespaceAnalyzer` and `SemanticAnalyzer` (extending `analyzer_factory` with an `analyzer_cls` parameter), covering both `Tags:` layouts, `Tags:` as the first line, suite/test documentation not checked, no-report on RF < 7.5 and modifier suppression; pure-function tests for the row computation; nothing under `data/tests/versions/`, so no regression baselines change.

## Risks / Trade-offs

- [Flag parity broken by wiring one analyzer only] → parametrised tests over both.
- [Cached diagnostics appear only after the release bump] → expected (`app_version` keyed cache).
- [RF's `header_re` false positives (prose line `Tags: …`)] → same as RF; suppressible.
- [False negative for `Tags:` behind an escaped `\n` inside one `[Documentation]` row] → RF unescapes before parsing and warns at run time for such a layout, while the source-row rule sees a single line; accepted (rare layout), documented with the diagnostic.

## Migration Plan

Additive diagnostic; users can suppress the code with the existing modifiers. No data changes.
