# Design: deprecation-diagnostics

## Context

See proposal.md. Verified facts:

- **RF 7.5.** `Languages.deprecations` maps `old.title()` → `(new, version)` and also maps the old term to the English name in `headers`/`settings`, which is why old terms still lex without any token error; `get_deprecation()` is inert on 7.5 (active only when the running RF is newer than the deprecation version) and nothing calls it — warnings are announced for 7.6. Header tokens are matched by `normalize_whitespace(marker).strip('* ').title()`, settings by `normalize_whitespace(name).title()` with brackets stripped for local settings; tokens keep the original text. `docstringparser` recognises section headers with `[*_]*(args|…|tags)[*_]*::?[*_]*` (case-insensitive, `fullmatch` on the stripped line) and warns "Not having an empty row before 'Tags:' is deprecated." when a `tags` header follows a non-empty line; `KeywordImplementation.all_tags` runs that parser on every execution of a keyword whose documentation contains a `Tags:` header, so the warning repeats at run time. A `[Documentation]` value joins one entry per source row with `\n`; an empty continuation row yields an empty line, and the `Tags:` row's `CONTINUATION` token gives the indentation for an inserted row. Tag-pattern deprecations (`&`, operator-adjacent mixed-case operands) are reported by RF itself wherever patterns are applied, which `robotcode robot`, `discover --diagnostics` and `results` already surface; `list_`/`time_` are documentation-only.
- **RobotCode.** Deprecation diagnostics exist as copy-pasted code in both analyzers (`DEPRECATED_FORCE_TAG` information, `DEPRECATED_HYPHEN_TAG` warning only where RF warns, `DEPRECATED_HEADER` from RF's token error, `DEPRECATED_RETURN_SETTING`), each with `DiagnosticTag.DEPRECATED`; every diagnostic passes the modifiers, so new codes are suppressible automatically. The `semanticModel` flag defaults to off, `Namespace` picks the analyzer by flag, and `dev-docs/semantic-model.md` requires identical output under both flags until the legacy analyzer is deleted; `diagnostic_rules.py` is the precedent for analyzer-independent rule code. The `Languages` object reaches the analyzers (`self._languages`) and the language server (`namespace.languages`); the `Languages` stub lacks `deprecations`. Completion builds headers from the per-language tables (deprecated headers are therefore not offered) but settings from the aggregated table (deprecated settings offered unmarked); `CompletionItemTag.DEPRECATED` is available. Quick fixes follow a collect/resolve pattern keyed by diagnostic code. Observed on RF 7.5: a French/Finnish file with the deprecated terms and a legacy `Tags:` layout yields zero RobotCode diagnostics; on RF 7.4 the new terms are lexer errors.
- **Tests.** No analyzer test covers a `DEPRECATED_*` code, no `Language:` test data exists, the analyzer test helpers build a `SemanticAnalyzer` without languages; quick-fix pure-function tests and resolve tests exist in `test_code_action_quick_fixes_model.py`; no LS completion test suite exists.

## Goals / Non-Goals

**Goals:**
- Tell users about the two deprecations where they can act, with one-click fixes, before RF starts warning.
- Identical behaviour under both analysis paths; rules survive the legacy analyzer's removal.

**Non-Goals:**
- Diagnostics for Python library keywords with a legacy `Tags:` layout (no in-file position; a hover note could build on `support-rf75`'s helper later).
- Re-implementing RF's tag-pattern grammar (`config check`, model validators, CLI pre-checks) — RF 7.5 already warns at every RobotCode touch point, RF 8 will change the grammar anyway.
- A hint for `list_=`/`time_=` named arguments (documentation-only deprecation without a runtime warning; RF's own note in the Collections docstrings is already part of the rendered documentation after `support-rf75`, BuiltIn's `Sleep`/`Get Time` carry no such note).
- Hiding deprecated spellings from completion (mixed-version teams still need them).

## Decisions

### D1: Shared rule module wired into both analyzers

`packages/robot/src/robotcode/robot/diagnostics/deprecations.py` holds pure functions — `find_deprecated_header(token, languages)`, `find_deprecated_setting(token, languages)`, `find_tags_line_without_empty_row(documentation_node)` and the replacement computation — reproducing RF's normalisation (`title()`, bracket stripping, `header_re` and the `can_start` rule). Both analyzers add a few lines in `visit_SectionHeader`, generically in `visit()` for every statement whose first token type is in `Token.SETTING_TOKENS` (a custom language file may deprecate any setting, not only tag settings, so per-visitor wiring would miss e.g. a translated `Documentation`), and in `visit_DocumentationOrMetadata` (keyword context via the node stack), calling the helper and `_append_diagnostics`. Inline duplication (the existing pattern) was rejected as the maintenance hazard `semantic-model-cleanup` names; a post-pass visitor in `Namespace` was rejected because it would bypass `AnalyzerResult`, the snapshot harness and the "single producer" rule. The helper skips tokens that already carry an RF error, so a future RF that flags the terms itself does not produce duplicates. Module-scope `RF_VERSION >= (7, 5)` gating; the `Languages` stub gains `deprecations`.

### D2: Codes and severities

`DeprecatedTranslation` (one code for headers and settings, INFORMATION + Deprecated tag — RF 7.5 is silent, the replacement is an error on ≤ 7.4, and `DEPRECATED_FORCE_TAG` is the precedent for a soft nudge) and `TagsWithoutEmptyRow` (WARNING + Deprecated tag — RF warns on every execution). Message wording is RF's `get_deprecation()` text verbatim: "Section header 'Unités de test' has been deprecated since Robot Framework 7.5. Use 'Cas de test' instead." (kind capitalised: `Section header`/`Setting`); when a language file declares the version as `None`, the "since Robot Framework …" clause is omitted, as RF does.

### D3: Quick fixes recompute from the token

`code_action_replace_deprecated_translation` filters diagnostics by code and, on resolve, recomputes the replacement from the token text and `namespace.languages.deprecations` (no `Diagnostic.data`, no cache-format change), editing the middle of `^(\*+\s*)(.*?)(\s*\**)\s*$` for headers, the whole name for suite settings and `[` + new + `]` for local settings; title "Replace with 'Cas de test'". `code_action_insert_empty_row_before_tags` inserts `' ' * continuation_col + '...' + line ending` at the start of the `Tags:` row. Normalising to the configured header style was rejected: users keep their decoration.

### D4: Completion tags, never hides

The three settings-completion builders compare the `title()`-ed label with `languages.deprecations` and set `tags=[CompletionItemTag.DEPRECATED]`, `deprecated=True` and a later sort key; headers are untouched (already not offered). Deprecated spellings appear today only on the default path that uses the aggregated `languages.settings` table (`filterDefaultLanguage` off); the per-language branch used when `filterDefaultLanguage` is on builds items from `Language.settings`, which lacks them — that branch additionally offers the deprecated keys of each `Language.deprecations` whose replacement is a setting, tagged the same way, so "never hides" holds in both configurations.

### D5: Gating and tests

Both rules only on RF ≥ 7.5 (as `DEPRECATED_HYPHEN_TAG`: only where RF itself is involved, and never on versions where the fix would break). Tests: a new analyzer test module parametrised over `NamespaceAnalyzer` and `SemanticAnalyzer` built with `Languages(['fr', 'fi'])` (extending `analyzer_factory` with an optional `languages` parameter), covering header, suite setting, local setting, custom language file, no-report on RF < 7.5, no duplicate when RF sets a token error, modifier suppression, and both `Tags:` layouts; pure-function tests for the two edit computations; a completion unit test with a stub namespace; nothing under `data/tests/versions/`, so no regression baselines change.

## Risks / Trade-offs

- [Flag parity broken by wiring one analyzer only] → parametrised tests over both.
- [RF 7.6 starts flagging the terms itself → double report] → helper skips tokens with an RF error; re-check against 7.6 sources.
- [Cached diagnostics appear only after the release bump] → expected (`app_version` keyed cache).
- [RF's `header_re` false positives (prose line `Tags: …`)] → same as RF; suppressible.
- [False negative for `Tags:` behind an escaped `\n` inside one `[Documentation]` row] → RF unescapes before parsing and warns at run time for such a layout, while the source-row rule sees a single line; accepted (rare layout), documented with the diagnostic.
- [Mixed-version teams pushed to a term RF ≤ 7.4 rejects] → INFORMATION severity, version in the message and fix title.
- [Completion tag rendering in IntelliJ not verifiable here] → manual check.

## Migration Plan

Additive diagnostics; users can suppress the codes with the existing modifiers. No data changes.
