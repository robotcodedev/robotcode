# Design: semantic-model-sidecar-cleanup

## Context

The SemanticModel migration follows an established pattern (see `dev-docs/semantic-model.md`, Tiers 1–2, commits `23a538cb` … `6a3d5a39`): each LSP feature branches on `namespace.semantic_model` — model path when the `robotcode.experimental.semanticModel` flag is on, legacy `ModelHelper`/AST path otherwise — with a dedicated `test_*_model.py` equivalence suite. Six files outside the tier plan still import `ModelHelper`. The 2026-07-19 audit classified them:

| File | ModelHelper usage |
|---|---|
| `http_server.py`, `keywords_treeview.py` | mixin inherited, **zero** calls |
| `hover.py`, `references.py`, `rename.py` | mixin inherited, **zero** calls — the design document's Tier 3 description is stale (these were rewritten onto reference dicts before the SemanticModel work; hover.py is 289 LOC today, not ~850) |
| `code_lens.py` | `get_keyword_definition_at_line()` — 3-line static lookup, sole LSP caller |
| `selection_range.py` | `iter_variables_from_token()` |
| `inline_value.py`, `debugging_utils.py` | `iter_variables_from_token`, `iter_expression_variables_from_token`, `get_expression_statement_types` |

## Goals / Non-Goals

**Goals:**
- Remove the `ModelHelper` dependency from the six sidecar files as far as possible today; where a legacy fallback must remain (flag off), confine `ModelHelper` usage to that fallback.
- Identical feature output under both flag states.
- Complete the `PYTHON_VARIABLE_REF`-in-builder promise from the design document's elimination table for expression-context tokens.

**Non-Goals:**
- No Tier 3/4 migration (hover, references, rename, completion).
- No deletion of `ModelHelper` itself (Phase 4).
- No behavior improvements — pure parity refactor. Improvements enabled by the model (e.g. richer inline values) go to the design doc's Ideas Collection instead.

## Decisions

### D1: Two migration modes — flag-independent vs. flag-gated

`http_server.py`, `keywords_treeview.py`, `hover.py`, `references.py`, `rename.py` (dead mixin) and `code_lens.py` (analyzer-independent static lookup) are migrated **unconditionally** — no flag branch, `ModelHelper` import disappears entirely. The three variable-based features get the standard **model branch + legacy fallback**, because their legacy path genuinely re-resolves via `ModelHelper` and must keep working while the flag defaults to `false`.

*Alternative considered*: flag-gating everything uniformly — rejected; a flag branch around a dead mixin or a pure `LibraryDoc` lookup adds a code path without any payoff.

### D2: code_lens inlines the lookup — no new shared helper

`get_keyword_definition_at_line()` is `next((k for k in library_doc.keywords.keywords if k.line_no == line), None)`. `code_lens.py` is its only LSP caller, and `semantic_analyzer/analyzer.py` already carries its own private copy (`_get_keyword_definition_at_token`). Inline the expression (or a private module function) in `code_lens.py`.

*Alternative considered*: promoting the helper to `LibraryDoc` — rejected; two private call sites don't justify new public API (no unasked infrastructure).

### D3: Model path reads sub-tokens; expression refs are added to the builder first

- `selection_range.py`: the structural part of the hierarchy (node chain → statement → token) **stays on the AST walk** — `SemanticNode` carries only `line_start`/`line_end`, no columns, so it cannot reproduce the column-precise `range_from_node()` ranges. Only the innermost step (variable range under the cursor, legacy `iter_variables_from_token(..., return_not_found=True)`) switches to model sub-tokens (`VARIABLE` **and** `VARIABLE_NOT_FOUND`). That is sufficient — the AST walk is structural, not resolution, and `ModelHelper` disappears from the file.
- `inline_value.py` / `debugging_utils.py`: additionally need `(range, VariableDefinition)` pairs → `model.find_variable()` per variable sub-token, and `$var` expression references in conditions. **Resolution position is the debugger's stopped location** (`context.stopped_location.start` / request position), not the token's own line — the legacy path resolves visibility there and the model path must pass the same line to `find_variable()`. Unlike selection_range, these two only report *found* definitions (no `return_not_found`).
- **Prerequisite**: the analyzer currently renders `PYTHON_VARIABLE_REF` sub-tokens only inside `${{...}}` bodies; bare `$var` refs on `CONDITION` tokens (`IF $x > 1`) are analyzed for references/diagnostics (`_analyze_token_expression_variables`) but not rendered as sub-tokens. Extend `_build_token_with_var_subtokens` (or the CONDITION builders) to attach `PYTHON_VARIABLE_REF` sub-tokens from the same `_iter_expression_variables_from_token` positions. This is the elimination-table mapping "`iter_expression_variables_from_token` → IN BUILDER" — Tier 3 hover will need it too.
- `get_expression_statement_types()` (AST `isinstance` gate for expression contexts) becomes unnecessary on the model path: expression context is encoded as `TokenKind.CONDITION`.

*Alternative considered*: model path calls the legacy helper just for `$var` conditions — rejected; mixing `ModelHelper` into the model path defeats the migration and leaves a hidden dependency for Phase 4.

### D4: Test strategy mirrors the existing `test_*_model.py` pattern

- New equivalence tests for selection range and inline value (dual-protocol or flag-parametrized, following `test_inlay_hint_model.py` / `test_semantic_tokens_flag_parity.py`).
- `debugging_utils.py` has no LSP E2E harness (debug-time); cover its variable-extraction path with unit tests against a built model, both flag states.
- Analyzer-side: extend `test_variable_tokenizer.py` / snapshot tests for `PYTHON_VARIABLE_REF` on CONDITION tokens; `test_variable_pipeline_comparison.py` must stay green (sub-token rendering must not change diagnostics/references).

## Risks / Trade-offs

- [Sub-token positions differ subtly from legacy `iter_variables_from_token` ranges (e.g. index access, extended syntax)] → equivalence tests compare exact ranges; any mismatch is a bug in one of the paths and gets resolved in favor of documented RF semantics, xfail-documented if legacy is wrong (precedent: known parity exceptions table in the design doc).
- [`PYTHON_VARIABLE_REF` rendering on CONDITION changes semantic-token output] → currently impossible: `collect_tokens_from_model()` does not descend into `sub_tokens` at all (review 2026-07-19), so new sub-tokens are invisible to Tier 1 output. The guard suites are the analyzer snapshots and `test_variable_pipeline_comparison.py` (diagnostics/references must not change). Note: `test_semantic_tokens_flag_parity.py` is currently vacuous (flag never reaches the server) — do **not** rely on it until `semantic-model-tier1-completion` fixes the fixture.
- [debugging_utils runs while the debugger holds a stopped location; model may be stale relative to the running file] → same staleness exposure as the legacy AST path (both read the cached namespace); no new risk, documented only.

## Migration Plan

Single PR, ordered commits: (1) dead-mixin removals + code_lens inline (safe, flag-independent), (2) analyzer `PYTHON_VARIABLE_REF` on CONDITION + tests, (3) selection_range, (4) inline_value + debugging_utils, (5) design-doc checklist update. Rollback = revert; flag default remains `false` throughout.

## Open Questions

- None blocking. Whether `keywords_treeview.py` / `http_server.py` ever needed the mixin historically is irrelevant to removal (no call sites today).
