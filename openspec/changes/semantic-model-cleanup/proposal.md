# Proposal: semantic-model-cleanup

## Why

Phase 4 of the SemanticModel migration (`dev-docs/semantic-model.md`) is the final cleanup: once the SemanticModel is the default and every feature runs on it (Phase 3, `semantic-model-switchover`), the parallel legacy machinery is pure dead weight and a maintenance hazard (every fix must be mirrored into both analyzers). This change deletes it: the legacy fallback paths in each migrated LSP feature, the feature flag, and the three retired subsystems — `NamespaceAnalyzer` (~100 KB, [namespace_analyzer.py](../../../packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py)), `ModelHelper` (~790 LOC, [model_helper.py](../../../packages/robot/src/robotcode/robot/diagnostics/model_helper.py)), and `ScopeTree` (~200 LOC, [scope_tree.py](../../../packages/robot/src/robotcode/robot/diagnostics/scope_tree.py)). The design document estimates ~3400+ LOC removed.

The `Namespace` scope API (`find_variable`, `get_variable_matchers`, `get_resolvable_variables`, [namespace.py:334-354](../../../packages/robot/src/robotcode/robot/diagnostics/namespace.py)) still delegates to `self._scope_tree`; it must be redirected to the `SemanticModel` before `ScopeTree` can be deleted.

## What Changes

- **Remove legacy fallback paths** from every migrated LSP feature (the `else` branches that ran `ModelHelper`/AST when the flag was off): semantic tokens, inlay hints, signature help, all code actions, hover, completion, selection range, inline value, debugging utils. Each feature becomes model-only.
- **Redirect the `Namespace` scope API** to the model: `find_variable` → `model.find_variable`, `get_variable_matchers` / `get_resolvable_variables` → `model.get_variables_at` (with resolution). Remove `ScopeTreeBuilder` usage and the `local_scopes` field from `NamespaceData` (the pickled model already carries `DefinitionBlock.local_variables`).
- **Remove the feature flag** `robotcode.experimental.semanticModel` (`package.json`, `workspace_config.py`, `document_cache_helper.py`, `set_semantic_model_enabled`) — the model is unconditional.
- **Delete** `namespace_analyzer.py`, `model_helper.py`, `scope_tree.py`.
- **Remove Level-E** comparison/performance tests (the old analyzer they compared against is gone) and **simplify Level-D** (drop the flag parameterization — there is only one path).
- **Reorganize the design doc**: with the migration finished, extract the data-structure/API reference from `dev-docs/semantic-model.md` into a code-adjacent `semantic_analyzer/README.md` (the living reference of the shipped model), trim the now-historical migration narrative to a short design rationale (or remove it — git history and archived changes preserve the "why"), and move any remaining un-proposed ideas to a backlog.

## Capabilities

### New Capabilities

- `semantic-model-sole-implementation`: The SemanticModel/`SemanticAnalyzer` is the only analysis and query path — legacy fallbacks, the feature flag, `NamespaceAnalyzer`, `ModelHelper`, and `ScopeTree` are removed, and the `Namespace` scope API delegates to the model.

### Modified Capabilities

_None — the change-local specs from the other semantic-model changes are not yet archived into main specs. This change removes fallback code the earlier changes deliberately retained; those retained paths were never captured as main-spec requirements._

## Impact

- **Code**: deletes `packages/robot/.../namespace_analyzer.py`, `model_helper.py`, `scope_tree.py`; edits `namespace.py` (scope API + `NamespaceData`), `document_cache_helper.py`, `workspace_config.py`, `package.json`, and removes the `else` fallback in every migrated LSP feature part. ~3400+ LOC net removal.
- **Tests**: remove Level-E (`test_variable_pipeline_comparison.py`, `test_analyzer_performance.py`, `test_nested_variable_resolution.py`'s parity halves); simplify Level-D (remove flag parameterization); every `test_*_model.py` becomes the single-path test.
- **Docs**: extract the data-structure/API reference from `dev-docs/semantic-model.md` into a code-adjacent `semantic_analyzer/README.md` (living reference of the shipped model); trim the historical migration narrative to a short rationale or remove it; mark the feature-flag / transition-period passages historical. Phase-4 completion is tracked in OpenSpec.
- **Dependency (HARD GATE)**: MUST come after `semantic-model-switchover` is complete and stable (flag default `true`, no reported regressions). This is the second of only two hard gates: deleting `NamespaceAnalyzer`/`ModelHelper`/`ScopeTree` and the fallbacks is only safe once nothing reaches them. This is the point of no return — after deletion the legacy path cannot be re-enabled by config; rollback is git revert only. Not breaking for users (behavior unchanged); breaking for any out-of-tree code importing `NamespaceAnalyzer`/`ModelHelper`/`ScopeTree`.
