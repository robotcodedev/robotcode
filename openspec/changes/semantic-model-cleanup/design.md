# Design: semantic-model-cleanup

## Context

After `semantic-model-switchover`, every LSP feature runs on the model by default, but the legacy scaffolding is still present: an `else` fallback in each migrated feature, the feature flag, the two analyzers (`SemanticAnalyzer` active, `NamespaceAnalyzer` dormant), `ModelHelper` (imported only from fallbacks now), and `ScopeTree` (still backing the `Namespace` scope API). The design document's ModelHelper-elimination table and ScopeTree-migration mapping specify exactly what replaces each.

The one non-mechanical part is the `Namespace` scope API: `find_variable` / `get_variable_matchers` / `get_resolvable_variables` currently call `self._scope_tree`. The model provides `find_variable(name, line)` and `get_variables_at(line)`; `DefinitionBlock.local_variables` + `file_scope` already carry everything `ScopeTree` held, and `from_data()` already rebuilds them. So the API can delegate to the model and `ScopeTree` drops out.

## Goals / Non-Goals

**Goals:**
- Single implementation: model-only feature paths, no flag, no legacy analyzers/helpers.
- `Namespace` scope API delegates to the SemanticModel.
- Net ~3400+ LOC removed, per the design doc estimate.

**Non-Goals:**
- No behavior change (this is deletion of now-unreachable-by-default code, guarded by the tests that already prove parity).
- No new features (Phase 5).
- No change to the model shape or the `SemanticAnalyzer` itself.

## Decisions

### D1: Delete fallbacks feature-by-feature, tests stay green each step

Each migrated feature's `if model := namespace.semantic_model: … else: …` collapses to the model body. Because the flag now defaults `true` and the model path is proven, the `else` is dead in practice; removing it is mechanical. Do it one feature per commit so a regression is bisectable to a single feature.

### D2: Scope API migration is the gating prerequisite for `ScopeTree` deletion

`ScopeTree` cannot be deleted while `Namespace.find_variable`/`get_variable_matchers`/`get_resolvable_variables` call it. Redirect those three to `model.find_variable` / `model.get_variables_at` first (the model is always present post-switchover), remove `ScopeTreeBuilder` usage and the `local_scopes` field from `NamespaceData`, then delete `scope_tree.py`. `get_resolvable_variables` adds a resolution step on top of `get_variables_at` — port that logic, don't drop it.

*Alternative considered*: keep a thin `ScopeTree` shim over the model — rejected; that preserves the very indirection this phase removes (no unasked infrastructure).

### D3: Flag removal is last among the config edits

Remove the flag only after all fallbacks are gone — otherwise a half-removed flag leaves features branching on a setting that no longer exists. Order: fallbacks → scope API → flag/config → delete `NamespaceAnalyzer`/`ModelHelper`/`scope_tree.py`.

### D4: Level-E goes, Level-D simplifies

Level-E tests compare against `NamespaceAnalyzer` (`test_variable_pipeline_comparison.py`, the parity halves of `test_nested_variable_resolution.py`) and benchmark relative to it — meaningless once it is deleted; remove them. Level-D (the flag-parametrized fixture from switchover) collapses to a single path; drop the parameterization but keep the assertions as plain single-path tests. The `test_*_model.py` suites simply become *the* tests.

## Risks / Trade-offs

- [A fallback path silently did something the model path does not (an unnoticed non-parity)] → the switchover harness already asserted cross-feature parity with the flag on; deleting the proven-dead `else` cannot change default behavior. Any latent gap would already have failed switchover.
- [`get_resolvable_variables` resolution semantics differ subtly from the scope-tree version] → port and unit-test that method against the pre-change behavior before deleting `ScopeTree`; it is the one API with logic beyond a straight lookup.
- [Out-of-tree importers of the deleted classes break] → these are internal diagnostics classes; note the removal in the release notes. No public API guarantee covered them.

## Migration Plan

Ordered commits: (1) remove fallbacks per feature (several commits), (2) redirect `Namespace` scope API to the model + drop `local_scopes`/`ScopeTreeBuilder`, (3) remove the flag + config plumbing, (4) delete `namespace_analyzer.py` / `model_helper.py` / `scope_tree.py`, (5) remove Level-E + simplify Level-D, (6) design-doc Phase 4 ticks + prune transition sections. Rollback = git revert (no runtime toggle remains by design).

## Open Questions

- Are there fallback-only helpers (e.g. BDD-regex constants, argument-splitting utilities) that live in `ModelHelper` but are still imported by non-LSP code (`debugging_utils`, generated bundles)? Grep before deletion; anything still needed moves to its single remaining call site rather than keeping `ModelHelper` alive.
