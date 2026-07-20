# Proposal: semantic-model-sidecar-cleanup

## Why

The SemanticModel migration (see `dev-docs/semantic-model.md`) has completed Tier 1 (Semantic Tokens) and Tier 2 (Inlay Hints, Signature Help, all Code Actions). Phase 4 — deleting `ModelHelper` (~790 LOC) — is blocked by every remaining consumer. Six LSP files sit **outside** the Tier 1–4 migration plan and still import `ModelHelper`. The audit (2026-07-19) showed their dependency is far shallower than the tiered features: two files inherit the mixin without calling a single method, one uses a 3-line static lookup, and three use only the variable-iteration helpers. Clearing them now is cheap and removes six of the remaining Phase 4 blockers before the heavy Tier 3/4 work starts.

## What Changes

- `http_server.py` and `keywords_treeview.py`: remove the dead `ModelHelper` mixin from the class bases — no call sites exist.
- `hover.py`, `references.py`, `rename.py`: remove the dead `ModelHelper` mixin as well. Follow-up audit (2026-07-19) showed the design document's Tier 3 description is stale — all three files only inherit the mixin without calling a single member (they work via pre-computed reference dicts). This empties "Tier 3" of its ModelHelper dependency; the optional hover-on-model value migration moves to the separate `semantic-model-hover` change.
- `code_lens.py`: replace the single `get_keyword_definition_at_line()` call with a local lookup on `namespace.library_doc` (the helper is a 3-line `next()` over `library_doc.keywords.keywords`; code_lens is its only LSP caller) and remove the mixin.
- `selection_range.py`: read variable ranges from pre-computed VARIABLE sub-tokens via `namespace.semantic_model` when available; keep the `iter_variables_from_token()` path as legacy fallback (flag off).
- `inline_value.py`: build inline values from model sub-tokens (`VARIABLE`, `PYTHON_VARIABLE_REF`) plus `model.find_variable()` when available; legacy fallback stays.
- `debugging_utils.py`: same pattern as `inline_value.py` (same ModelHelper method trio, evaluated at the debugger's stopped location).
- No user-visible behavior change in any feature. Model-path output must equal legacy-path output.

## Capabilities

### New Capabilities

- `semantic-model-sidecar-consumers`: The six sidecar LSP features (code lens, selection range, inline value, debugging utils, keywords treeview, HTTP server) obtain analysis data without `ModelHelper` re-resolution where possible, and — for the three variable-based features — read pre-resolved SemanticModel data when the `robotcode.experimental.semanticModel` flag is active, with output parity between both paths.

### Modified Capabilities

_None — no existing main specs; this change introduces the first spec for these features._

## Impact

- **Code**: `packages/language_server/src/robotcode/language_server/robotframework/parts/` — `http_server.py`, `keywords_treeview.py`, `hover.py`, `references.py`, `rename.py`, `code_lens.py`, `selection_range.py`, `inline_value.py`, `debugging_utils.py`. One small addition in `packages/robot/` (`semantic_analyzer/analyzer.py`): attach `PYTHON_VARIABLE_REF` sub-tokens to expression-context tokens (CONDITION), completing the `iter_expression_variables_from_token → IN BUILDER` mapping already promised in the design document's ModelHelper-elimination table.
- **Tests**: new model-parity tests for selection range and inline value (pattern: existing `test_*_model.py` files); existing E2E suites must stay green under both flag states.
- **Docs**: reflect the resolved sidecar consumers in `dev-docs/semantic-model.md` (Impact-on-LSP section) if relevant; progress itself is tracked in OpenSpec, not in the doc.
- **Dependencies/Breaking**: none. `ModelHelper` itself is untouched; its deletion remains a Phase 4 concern.
