# Proposal: semantic-model-switchover

## Why

Phase 3 of the SemanticModel migration (`dev-docs/semantic-model.md`) is the verification-and-switch milestone: once every LSP feature runs on the model behind the flag, the flag defaults to `true`, `Namespace` uses `SemanticAnalyzer` as its sole analyzer, the now-redundant `KeywordTokenAnalyzer` (~400 LOC, still live at [semantic_tokens.py:640](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py)) is removed, and the first genuinely *new* semantic-tokens capability — variable type modifiers (local/global/builtin/environment) — is enabled. None of this exists yet: the flag defaults to `false` in both `package.json` and `workspace_config.py`, and there is no cross-feature verification harness (no global Level-D flag fixture, no `test_analyzer_performance.py` for Level E).

This is the gate that makes the SemanticModel the default. It must not flip until the verification harness proves parity across *all* migrated features and confirms the performance/memory budget from the design doc.

## What Changes

- **Verification harness (must land first, flag still `false`):**
  - A shared **Level-D fixture** that runs the existing LSP snapshot/regtest suites under both flag states and asserts identical output across all migrated features (semantic tokens, inlay hints, signature help, code actions, hover, completion, selection range, inline value).
  - **Level-E performance benchmarks** (`test_analyzer_performance.py`): `SemanticAnalyzer` ≤ 30% slower than `NamespaceAnalyzer`; `SemanticModel` ≤ 500 KB/file (pickle-size estimate); pickle round-trip + `resolve_references()` ≤ 50 ms/file.
- **The switch:**
  - Flip `robotcode.experimental.semanticModel` default to `true` (`package.json` + `workspace_config.py`).
  - `Namespace` uses `SemanticAnalyzer.run()` as the sole source of all `AnalyzerResult` outputs (it already produces the superset).
- **Post-switch cleanups that only make sense once the model path is default:**
  - Remove `KeywordTokenAnalyzer` (the model renderer owns semantic tokens after `semantic-model-tier1-completion`).
  - Add variable type modifiers as a new semantic-tokens capability, derived from `model.find_variable()` variable types.

## Capabilities

### New Capabilities

- `semantic-model-default`: The SemanticModel is the default analysis path — the flag defaults to `true`, `Namespace` runs only `SemanticAnalyzer`, and the switch is gated by a cross-feature parity harness plus performance/memory budgets.
- `semantic-model-variable-modifiers`: Semantic tokens carry variable type modifiers (local/global/builtin/environment) derived from resolved `VariableDefinition` types — a capability the legacy `KeywordTokenAnalyzer` path did not provide.

### Modified Capabilities

_None — the change-local specs from the other semantic-model changes are not yet archived into main specs, so there is nothing to modify. Interaction with `semantic-model-tier1-parity` is a dependency (the repaired parity suite guards the `KeywordTokenAnalyzer` removal), not a spec modification._

## Impact

- **Code**: `package.json`, `packages/robot/.../workspace_config.py` (default flip); `packages/robot/.../namespace.py` + `document_cache_helper.py` (sole-analyzer selection); `packages/language_server/.../parts/semantic_tokens.py` (remove `KeywordTokenAnalyzer`, add modifier column).
- **Tests**: new global Level-D fixture; new `test_analyzer_performance.py`; all existing LSP suites must pass with the flag defaulting on.
- **Docs**: update `dev-docs/semantic-model.md` (Impact / Ideas sections) if affected; Phase-3 completion is tracked in OpenSpec, not in the doc.
- **Dependency (HARD GATE)**: MUST come after **all** feature migrations are complete — `semantic-model-tier1-completion`, `semantic-model-sidecar-cleanup`, `semantic-model-hover`, `semantic-model-completion`. This is one of only two hard gates in the whole migration (the other is `semantic-model-cleanup`): flipping the default with an unmigrated feature would ship the legacy fallback as the de-facto path, defeating the switch. This is a user-visible default change (behavior should be identical, but the analysis path changes for everyone); it is the deliberate go/no-go gate. Not breaking by intent — guarded by the harness. The legacy `NamespaceAnalyzer`/`ModelHelper`/`ScopeTree` remain in the tree (deleted in `semantic-model-cleanup`).
