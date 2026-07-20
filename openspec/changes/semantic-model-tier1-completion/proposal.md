# Proposal: semantic-model-tier1-completion

## Why

The proposal review on 2026-07-19 uncovered that Tier 1 (Semantic Tokens) is **not** actually verified, contrary to what the design document claimed: `test_semantic_tokens_flag_parity.py` sets the feature flag as the literal settings key `"robotcode.experimental"`, while the workspace settings lookup navigates dot-split nested keys — the flag never reaches the server, `protocol_new` silently runs the legacy path, and the test compares legacy against legacy (proven by replicating the lookup: it yields `{}`). Independently, `collect_tokens_from_model()` iterates only flat `stmt.tokens` — it descends into neither `sub_tokens` (variables inside arguments) nor `RunKeywordCallStatement.inner_calls` (inner keyword names stay ARGUMENT-kind in the outer token list), and emits no context modifiers (builtin/local). The `_TOKEN_KIND_TO_SEM_TOKEN` map already contains all sub-token kinds as dead entries. Real Tier 1 parity is the foundation the whole migration's verification story rests on ("if semantic tokens match, the model is correct for all other consumers") — it must be completed before the flag can ever default to `true`.

## What Changes

- Fix the parity-test fixture: pass the flag as properly nested settings (`{"robotcode": {"experimental": {"semantic_model": true}}}`), and add a **vacuity guard** — the fixture asserts that `namespace.semantic_model` is actually populated in `protocol_new` so the suite can never silently degrade again.
- Extend `collect_tokens_from_model()` to full-fidelity rendering:
  - recursive `sub_tokens` descent (emit leaves instead of the parent when sub-tokens exist, matching legacy fragment output),
  - `RunKeywordCallStatement.inner_calls` traversal, position-merged with the outer token stream (inner keyword names render as KEYWORD, not ARGUMENT),
  - context modifiers matching the legacy path (e.g. builtin keyword, builtin/local/environment variable modifiers) via `stmt.keyword_doc` / `model.find_variable()`.
- Measure real parity across all `.robot` test data; fix model-side gaps; document any deliberate deviations as xfails with reasons (precedent: known parity exceptions table).
- Correct the design document's Tier 1 status once parity is genuinely green.

## Capabilities

### New Capabilities

- `semantic-model-tier1-parity`: The model-based semantic-tokens path produces output identical to the legacy path for every construct in the LSP test data, verified by a non-vacuous dual-protocol parity suite.

### Modified Capabilities

_None — no existing main specs cover semantic tokens._

## Impact

- **Code**: `packages/language_server/.../parts/semantic_tokens.py` (`collect_tokens_from_model` and the `_TOKEN_KIND_TO_SEM_TOKEN` map's modifier column); possibly small analyzer additions if rendering reveals missing token data.
- **Tests**: `test_semantic_tokens_flag_parity.py` (fixture fix + vacuity guard); expected initial red phase while gaps are fixed — xfail list documents anything deliberately deviating.
- **Docs**: update the Semantic Tokens entry in `dev-docs/semantic-model.md` (Impact-on-LSP section) if the parity outcome changes it; progress is tracked in OpenSpec.
- **Dependencies**: interacts with `semantic-model-sidecar-cleanup` (its `PYTHON_VARIABLE_REF`-on-CONDITION sub-tokens become visible to Tier 1 output once sub-token descent lands — legacy renders expression variables in conditions, so both pieces are needed for parity on those lines). Not breaking; flag default stays `false`.
