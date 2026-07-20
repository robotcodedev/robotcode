# Proposal: semantic-model-call-hierarchy

## Why

Call Hierarchy (`textDocument/prepareCallHierarchy`, `callHierarchy/incomingCalls`, `callHierarchy/outgoingCalls`) is the design document's top Phase 5 priority (P1, "High impact — most requested missing feature; Low effort — model makes it trivial"). The LSP types already exist ([core/lsp/types.py:1059+](../../../packages/core/src/robotcode/core/lsp/types.py) — `CallHierarchyItem`, `CallHierarchyIncomingCall`, `CallHierarchyOutgoingCall`, params), but there is **no handler**: a workspace grep for `call_hierarchy` in the language server returns nothing. Before the SemanticModel it was prohibitively expensive (a `find_keyword` per call site across the workspace); now every `KeywordCallStatement` carries a pre-resolved `keyword_doc` and every `RunKeywordCallStatement` exposes resolved `inner_calls`, so both directions are direct iterations over `model.statements` plus the already-aggregated `keyword_references`.

## What Changes

- Add a Call Hierarchy protocol part in the language server: `prepare` (keyword/test under the cursor → `CallHierarchyItem` via `model.statement_at()` / `token_path_at()`), `outgoingCalls` (walk the definition's body for `KeywordCallStatement`s + `RunKeywordCallStatement.inner_calls`, resolve via `keyword_doc`), `incomingCalls` (reverse lookup via the pre-aggregated `keyword_references` across workspace models).
- Register the capability with the client (declare `callHierarchyProvider`) and wire it into the VS Code extension where analogous providers are wired.
- This is a **net-new feature** gated on the SemanticModel being the analysis path; it has no legacy equivalent to keep parity with.

## Capabilities

### New Capabilities

- `semantic-model-call-hierarchy`: RobotCode answers LSP call-hierarchy requests for keywords and test cases — outgoing calls from a definition's body (including Run Keyword inner calls) and incoming calls from anywhere in the workspace — using pre-resolved SemanticModel data.

### Modified Capabilities

_None — no existing call-hierarchy handler exists._

## Impact

- **Code**: new `packages/language_server/.../parts/call_hierarchy.py`; registration in the protocol/capabilities wiring; a helper to enumerate `KeywordCallStatement`s within a definition body (shared with Phase 5 workspace features). Reads `keyword_references` and per-file `SemanticModel`s from the document cache.
- **Tests**: new `test_call_hierarchy.py` — prepare/incoming/outgoing over test data covering plain calls, namespace-qualified calls, BDD-prefixed calls, Run Keyword inner calls, and cross-file callers.
- **Docs**: update the Workspace-Level Features entry in the Ideas section of `dev-docs/semantic-model.md` to reflect the shipped feature; user-facing docs/news entry for the new feature.
- **Sequencing (soft)**: needs the SemanticModel available and correct (after `semantic-model-sidecar-cleanup` + `semantic-model-tier1-completion`). Recommended after `semantic-model-switchover` so `keyword_doc`/`inner_calls`/`keyword_references` are reliably populated workspace-wide; can also run flag-gated earlier. No hard ordering against the other Phase 5 changes. Not breaking; purely additive.
