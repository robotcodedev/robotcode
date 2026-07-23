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

### D3: Model path uses a shared value-scan port plus pre-computed expression refs (revised during implementation)

- `selection_range.py` / `debugging_utils.py`: the structural part (node chain → statement → token) **stays on the AST walk** — `SemanticNode` carries only `line_start`/`line_end`, no columns, so it cannot reproduce the column-precise `range_from_node()` ranges.
- **Revision of the original sub-token-lookup plan**: pre-computed `VARIABLE`/`VARIABLE_NOT_FOUND` sub-tokens turned out to be insufficient as the sole source — definition-name and assign-target cells carry no sub-structure, and the legacy `iter_variables_from_token` is value-based across *all* token types behind a tokenizer type gate (`Token.ALLOW_VARIABLES` + KEYWORD/ASSIGN/OPTION; `Token.VARIABLE` cells processed whole and raw-sliced when nested). Reproducing its candidate semantics per-context from sub-tokens would have meant a different special case per builder. Instead, one shared module (`parts/model_variables.py`) ports the candidate semantics once, operating on the model statements' token values (kind-gated like the legacy type gate, `NodeKind`-aware for the `Token.VARIABLE`-vs-`Token.ASSIGN` distinction), and resolves through `SemanticModel.find_variable()` — no `ModelHelper`, no `Namespace` re-resolution. Bare-`$var` condition refs come from the pre-computed `PYTHON_VARIABLE_REF` sub-tokens.
- `inline_value.py` / `debugging_utils.py`: need `(range, VariableDefinition)` pairs → `model.find_variable()` per candidate. **Resolution position is the debugger's stopped location** (`context.stopped_location.start` / request position), not the token's own line. Unlike selection_range, these two only report *found* definitions (no `return_not_found`).
- `SemanticModel.find_variable()` grew the legacy resolution facets the consumers need: environment-variable lookup (`%{NAME=default}`), a raw mode (`extended=False`, the lookup legacy performs before its extended-syntax fallback), and column-aware visibility on the defining line (`[Arguments]` definitions become visible after their cell, assigns/embedded arguments from the start of their name — matching the legacy scope-tree registration). Two pre-existing `find_variable` bugs surfaced and were fixed: the local-scope matcher comparison called a non-callable (`matcher.match`), and `_normalize_variable_name` treated any space as extended syntax, breaking names with spaces (`${name with space}`).
- The analyzer prerequisite from the original plan holds: the CONDITION builders attach `PYTHON_VARIABLE_REF` sub-tokens (positions identical to `_iter_expression_variables_from_token`); the semantic-token renderer never emits them (model-only kinds policy).
- `get_expression_statement_types()` is not needed on the model path for inline values (expression context ≡ `TokenKind.CONDITION`); the debug fallback keeps the structural AST `isinstance` gate (a locally defined `(IfElseHeader, WhileHeader)` tuple, not the `ModelHelper` classmethod) because legacy scopes the expression fallback to the node under the cursor.

*Alternative considered*: model path calls the legacy helper just for `$var` conditions — rejected; mixing `ModelHelper` into the model path defeats the migration and leaves a hidden dependency for Phase 4.

### D4: Test strategy mirrors the existing `test_*_model.py` pattern

- New equivalence tests for selection range and inline value (dual-protocol, following `test_semantic_tokens_flag_parity.py`, including its vacuity guard). Positions are probed deterministically around every variable-syntax span of the corpus (capped per file; `very_big_file.robot` excluded — a generated performance corpus whose per-position probing would dominate the runtime).
- `debugging_utils.py` has no LSP E2E harness (debug-time); its extraction is exercised through the same dual-protocol pattern by calling the rpc handler directly at probed positions (both flag states, no `ModelHelper` on the model path).
- Analyzer-side: `test_analyzer.py` covers `PYTHON_VARIABLE_REF` on CONDITION tokens (IF / WHILE / inline IF, exact ranges, no `${x}` duplication); `test_variable_pipeline_comparison.py` and the semantic-tokens parity suite stay green (the renderer suppresses model-only kinds).

## Risks / Trade-offs

- [Sub-token positions differ subtly from legacy `iter_variables_from_token` ranges (e.g. index access, extended syntax)] → equivalence tests compare exact ranges; any mismatch is a bug in one of the paths and gets resolved in favor of documented RF semantics, xfail-documented if legacy is wrong (precedent: known parity exceptions table in the design doc).
- [`PYTHON_VARIABLE_REF` rendering on CONDITION changes semantic-token output] → currently impossible: `collect_tokens_from_model()` does not descend into `sub_tokens` at all (review 2026-07-19), so new sub-tokens are invisible to Tier 1 output. The guard suites are the analyzer snapshots and `test_variable_pipeline_comparison.py` (diagnostics/references must not change). Note: `test_semantic_tokens_flag_parity.py` is currently vacuous (flag never reaches the server) — do **not** rely on it until `semantic-model-tier1-completion` fixes the fixture.
- [debugging_utils runs while the debugger holds a stopped location; model may be stale relative to the running file] → same staleness exposure as the legacy AST path (both read the cached namespace); no new risk, documented only.

## Migration Plan

Single PR, ordered commits: (1) dead-mixin removals + code_lens inline (safe, flag-independent), (2) analyzer `PYTHON_VARIABLE_REF` on CONDITION + tests, (3) selection_range, (4) inline_value + debugging_utils, (5) design-doc checklist update. Rollback = revert; flag default remains `false` throughout.

## Open Questions

- None blocking. Whether `keywords_treeview.py` / `http_server.py` ever needed the mixin historically is irrelevant to removal (no call sites today).
