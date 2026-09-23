# Design: deprecation-diagnostics

## Context

See proposal.md. Verified facts:

- **RF 7.5.** `docstringparser` recognises section headers with `[*_]*(args|…|tags)[*_]*::?[*_]*` (case-insensitive, `fullmatch` on the line) and warns "Not having an empty row before 'Tags:' is deprecated." when a `tags` header comes at a place where no section may start (`_match_header`, with a `TODO` to require the empty row in RF 8 or 9). A section may start on the first line, after an empty line and inside a named section (`Args:`, `Returns:`, `Raises:` with their indented or empty lines) — so `Tags:` directly after the entries of an `Args:` section is not reported, while a prose line such as `tags: for grouping` after text is; `KeywordImplementation.all_tags` runs that parser on every execution of a keyword whose documentation contains a `Tags:` header, so the warning repeats at run time, and Libdoc's `update_docs` prints it once per keyword. The `value` of a `[Documentation]` statement is the text Robot Framework itself parses: one line per source row, an empty continuation row yields an empty line, and the additional indentation of a row such as `...        x: the x` is restored (the lexer treats it as a separator, `value` puts it back). Tag-pattern deprecations (`&`, operator-adjacent mixed-case operands) are reported by RF itself wherever patterns are applied; `list_`/`time_` are documentation-only. Deprecated translations: `Languages.deprecations` maps the old terms to the new ones and to the English names, which is why they lex without a token error; `get_deprecation()` has no caller on 7.5 or on master (7.5.1.dev1), and a French/Finnish file with the old terms runs without any warning — the warning waits for robotframework/robotframework#5210 (warnings in the parsing model, milestone 7.6).
- **RobotCode.** Deprecation diagnostics exist as copy-pasted code in both analyzers (`DEPRECATED_FORCE_TAG` information, `DEPRECATED_HYPHEN_TAG` warning only where RF warns, `DEPRECATED_HEADER` from RF's token error, `DEPRECATED_RETURN_SETTING`), each with `DiagnosticTag.DEPRECATED`; every diagnostic passes the modifiers, so a new code is suppressible automatically. The `semanticModel` flag defaults to off, `Namespace` picks the analyzer by flag, and `dev-docs/semantic-model.md` requires identical output under both flags until the legacy analyzer is deleted; `diagnostic_rules.py` is the precedent for analyzer-independent rule code. `get_docstring_info` in `library_doc.py` (`support-rf75`) calls `parse_docstring` under `LOGGER.cache_only`, so RF's warning is produced and discarded. Observed on RF 7.5: a keyword with the legacy `Tags:` layout yields zero RobotCode diagnostics.
- **Tests.** No analyzer test covers a `DEPRECATED_*` code; the analyzer test helper `analyzer_factory` builds a `SemanticAnalyzer`; `test_variable_pipeline_comparison.py` runs both analyzers on the texts in `_PARITY_CASES` and compares all diagnostics.

## Goals / Non-Goals

**Goals:**
- Show the deprecation Robot Framework warns about where the user can act.
- Identical behaviour under both analysis paths; the rule survives the legacy analyzer's removal.

**Non-Goals:**
- Deprecated translated headers and settings (`Unités de test`, `Tagit`, …): Robot Framework does not warn about them yet (maintainer decision: RobotCode reports deprecations only where RF warns); revisit when RF does, then with RF's `get_deprecation()` wording and a check that RF's own token warning is not duplicated.
- Diagnostics for Python library keywords with a legacy `Tags:` layout (no in-file position; a hover note could build on `support-rf75`'s helper later).
- Anything for tag patterns (`FooANDbar`, `a&b`), neither a diagnostic nor a documentation note (maintainer decision) — RF 7.5 already warns at every RobotCode touch point, RF 8 will change the grammar anyway.
- A hint for `list_=`/`time_=` named arguments (documentation-only deprecation without a runtime warning; RF's own note in the Collections docstrings is already part of the rendered documentation after `support-rf75`, BuiltIn's `Sleep`/`Get Time` carry no such note).

## Decisions

### D1: One rule function, called from both analyzer visitors

`diagnostic_rules.py` (the existing home of analyzer-independent rule code) gets `tags_line_without_empty_row(doc: str) -> Optional[int]`: RobotCode's own implementation of Robot Framework's rule — the section-header regular expression and the "may a section start here" state (first line, after an empty line, inside a named section) — returning the index of the first `Tags:` line RF would warn about. During planning the function was compared with RF 7.5's `parse_docstring` on 69,904 generated documentation layouts without a difference. Both analyzers call it in `visit_DocumentationOrMetadata` when the statement is the `[Documentation]` of a keyword (node stack), passing the statement's `value` — the text RF parses, with the restored indentation — and map the returned index to the `ARGUMENT` tokens of the corresponding source row (grouped by line) for the range; `_append_diagnostics` adds it. Until `semantic-model-switchover` the legacy `NamespaceAnalyzer` is the default path and must produce the same diagnostic; after `semantic-model-cleanup` only the `SemanticAnalyzer` call remains.

Rejected: a query over the `SemanticModel` (as `semantic-model-quality-diagnostics` plans for new checks) — the diagnostic would exist only with the flag on, the parity tests would have to exempt it, and the rule needs RF's `value` of the statement; catching the warning of `parse_docstring` in `get_docstring_info` — that runs while the library documentation is built, not while the file is analyzed, and the warning carries no position; subclassing RF's `DocStringParser` to reuse its logic — depends on RF's private `_parse_sections`/`_match_header` and on a module that exists only since RF 7.5; a separate `deprecations.py` module for one function. Module-scope `RF_VERSION >= (7, 5)` gating.

### D2: Code, severity and wording

`TagsWithoutEmptyRow`, WARNING with the Deprecated tag — RF warns on every execution. The message is exactly the one Robot Framework prints, with the keyword's name: "Invalid documentation in '<keyword>': Not having an empty row before 'Tags:' is deprecated."

### D3: No quick fix for now

A quick fix that inserts an empty continuation row before the `Tags:` row was planned and is left out by maintainer decision; it can be added later on top of the diagnostic code.

### D4: Gating and tests

Only on RF ≥ 7.5 (as `DEPRECATED_HYPHEN_TAG`: only where RF itself warns). Tests: the rule function with fixed examples (text then `Tags:`, empty row before, `Tags:` first, `Tags:` after an `Args:` section, a prose line `tags: …`, emphasis and `::` variants); the `SemanticAnalyzer` through the existing `analyzer_factory` (resource and suite keyword, correct layouts, suite/test/resource-file documentation not checked, no report on RF < 7.5, modifier suppression); the `NamespaceAnalyzer` through a new entry in `_PARITY_CASES` of `test_variable_pipeline_comparison.py`, which asserts identical diagnostics for both. No comparison test against `parse_docstring` (maintainer decision). Nothing under `data/tests/versions/`, so no regression baselines change.

## Risks / Trade-offs

- [Flag parity broken by wiring one analyzer only] → parity case in `test_variable_pipeline_comparison.py`.
- [Robot Framework changes the rule (announced for RF 8 or 9)] → the own implementation does not follow automatically; no comparison test against `parse_docstring` by maintainer decision, so it has to be revisited when the rule changes.
- [Cached diagnostics appear only after the release bump] → expected (`app_version` keyed cache).
- [RF's `header_re` false positives (prose line `Tags: …`)] → same as RF; suppressible.
- [False negative for `Tags:` behind an escaped `\n` inside one `[Documentation]` row] → RF unescapes before parsing and warns at run time for such a layout, while the source-row rule sees a single line; accepted (rare layout), documented with the diagnostic.

## Migration Plan

Additive diagnostic; users can suppress the code with the existing modifiers. No data changes.
