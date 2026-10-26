# Proposal: semantic-model-switchover

## Why

Phase 3 of the SemanticModel migration (`dev-docs/semantic-model.md`) is the verification-and-switch milestone: once every LSP feature answers the same with the flag on as with it off, the flag defaults to `true`, so `Namespace` runs `SemanticAnalyzer` instead of `NamespaceAnalyzer` for everyone who does not switch it off, and the first genuinely *new* semantic-tokens capability — the builtin modifier for variables — is enabled. None of this exists yet: the flag defaults to `false` in `package.json`, `workspace_config.py` and the IntelliJ settings; robot.toml and the editor setting are combined so that a `true` in either place enables the model, which would leave robot.toml and the CLI no way to switch it off once the editor default is `true`; and there is no cross-feature verification harness (no global Level-D flag fixture, no `test_analyzer_performance.py` for Level E).

This is the gate that makes the SemanticModel the default. It must not flip until the verification harness proves parity across *all* LSP features and confirms the performance/memory budget from the design doc.

## What Changes

- **Verification harness (must land first, flag still `false`):**
  - A shared **Level-D fixture** that runs the existing LSP snapshot/regtest suites under both flag states and asserts identical output across all features (semantic tokens, inlay hints, signature help, code actions, hover, completion, selection range, inline value). Hover and completion have no model branch: hover reads the reference lists and completion the namespace and the current text on both paths, and `test_hover_model.py` and `test_completion_model.py` (from `semantic-model-hover` and `semantic-model-completion`) already compare them under both flag states.
  - **Level-E performance benchmarks** (`test_analyzer_performance.py`): `SemanticAnalyzer` ≤ 30% slower than `NamespaceAnalyzer`; `SemanticModel` ≤ 500 KB/file (pickle-size estimate); pickle round-trip + `resolve_references()` ≤ 50 ms/file.
- **The switch:**
  - Flip the default of the flag to `true`: `robotcode.experimental.semanticModel` in `package.json` and `workspace_config.py`, the IntelliJ setting, and the `semantic-model` option of robot.toml when it is not set.
  - A `false` in robot.toml or in the editor setting switches the model off, the mirror of today's rule that a `true` in either place switches it on; the descriptions of the settings and the generated reference pages say so.
  - With the flag on, `Namespace` already runs only `SemanticAnalyzer` (it produces the superset of the `AnalyzerResult` outputs), so the analyzer selection needs no change.
- **After the switch:**
  - Add the builtin modifier to the name token of built-in variables, derived from the variable types the analyzer resolves. It is the one sanctioned difference between the two paths, which the parity comparisons ignore.

## Capabilities

### New Capabilities

- `semantic-model-default`: The SemanticModel is the default analysis path — the flag defaults to `true`, a `false` in robot.toml or in the editor setting switches it off, and the switch is gated by a cross-feature parity harness plus performance/memory budgets.
- `semantic-model-variable-modifiers`: The name token of a built-in variable carries the builtin modifier, derived from the resolved `VariableDefinition` type — a capability the legacy `KeywordTokenAnalyzer` path did not provide. Local, global and environment modifiers are not part of it (see design D4).

### Modified Capabilities

- `semantic-model-tier1-parity`: the model path's modifiers and encoded token data equal the legacy path's except for the builtin modifier on the name token of built-in variables, which only the model path sets.

## Impact

- **Code**: `package.json`, `packages/robot/.../workspace_config.py`, the IntelliJ settings (`intellij-client/.../configuration/`) and `packages/analyze/.../config.py` (defaults, setting descriptions); `packages/robot/.../document_cache_helper.py` (a `false` switches the model off); `packages/robot/.../semantic_analyzer/analyzer.py` and the mapping in `packages/language_server/.../parts/semantic_tokens.py` (builtin modifier on variable tokens).
- **Tests**: new global Level-D fixture; new `test_analyzer_performance.py`; the tests that compare both paths set the flag `false` explicitly for the legacy side, which today comes from the default; all existing LSP suites must pass with the flag defaulting on.
- **Docs**: the generated `etc/robot.toml.json`, `reference/vscode-settings.md` and `reference/config.md`; in `dev-docs/semantic-model.md` the Transition Period table and, if affected, the Impact / Ideas sections; Phase-3 completion is tracked in OpenSpec, not in the doc.
- **Dependency (HARD GATE)**: MUST come after **all** feature migrations are complete — `semantic-model-tier1-completion`, `semantic-model-sidecar-cleanup`, `semantic-model-hover`, `semantic-model-completion`; `semantic-model-hover` gives the model path the documentation targets of keywords in inline IF bodies and Run Keyword arguments and proves hover parity, hover itself keeps reading the references; `semantic-model-completion` proves completion parity, completion itself keeps its handlers. The builtin modifier also needs `semantic-tokens-variable-names`, which renders a token for the variable name only. This is one of only two hard gates in the whole migration (the other is `semantic-model-cleanup`): flipping the default with an unmigrated feature would ship the legacy fallback as the de-facto path, defeating the switch. This is a user-visible default change (behavior should be identical, but the analysis path changes for everyone); it is the deliberate go/no-go gate. Not breaking by intent — guarded by the harness. The legacy `NamespaceAnalyzer`/`ModelHelper`/`ScopeTree` and `KeywordTokenAnalyzer` remain in the tree (deleted in `semantic-model-cleanup`).
- **Follow-up**: `semantic-model-cleanup` removes `KeywordTokenAnalyzer` with the legacy semantic-tokens path (its task 2.1), and its removal of the flag (task 4.1) also covers the IntelliJ setting and the `semantic-model` option of robot.toml.
