# Design: semantic-model-cleanup

## Context

After `semantic-model-switchover`, the model is on by default and every LSP feature answers the same on it, but the legacy scaffolding is still present: an `else` fallback in the migrated features, `KeywordTokenAnalyzer` behind the semantic-tokens fallback, the feature flag (VS Code, IntelliJ, robot.toml, the namespace cache metadata), the two analyzers (`SemanticAnalyzer` active, `NamespaceAnalyzer` dormant), and `ModelHelper`. Outside the fallbacks only completion calls `ModelHelper` (seven calls to six of its methods: BDD prefix, the keyword of a call, the keyword prefix, the argument position); the `SemanticAnalyzer` does not import it.

The one non-mechanical part is the `Namespace` scope API: `find_variable` / `get_variable_matchers` / `get_resolvable_variables` call `self._scope_tree`, a `ScopeTree` that both analyzers build (the `SemanticAnalyzer` through `ScopeTreeBuilder`) and that `AnalyzerResult.scope_tree` and `NamespaceData.local_scopes` carry. Completion and hover read variables through it. The model provides `find_variable(name, line, col)` and `get_variables_at(line)`, and `DefinitionBlock.local_variables` + `file_scope` hold the same variables, restored by `from_data()`. `get_variables_at()` is unused so far and differs from `ScopeTree.get_variable_matchers()`: it compares lines only, where `find_variable()` and `ScopeTree` also use the column on the defining line, and it lets a lower-precedence file-scope variable override a higher one, where `ScopeTree` keeps local, command line, own, imported, built-in.

## Goals / Non-Goals

**Goals:**
- Single implementation: model-only feature paths, no flag, no legacy analyzers/helpers.
- `Namespace` scope API delegates to the SemanticModel.
- The three deleted files alone hold about 3400 lines.

**Non-Goals:**
- No behavior change (this is deletion of now-unreachable-by-default code, guarded by the tests that already prove parity).
- No new features (Phase 5).
- No change to the model shape or the `SemanticAnalyzer` itself, except that the analyzer stops building a `ScopeTree` and that `get_variables_at()` gets the visibility and precedence of `ScopeTree` (D2).

## Decisions

### D1: Delete fallbacks feature-by-feature, tests stay green each step

Each migrated feature's `if model := namespace.semantic_model: … else: …` collapses to the model body. Because the flag now defaults `true` and the model path is proven, the `else` is dead in practice; removing it is mechanical. Do it one feature per commit so a regression is bisectable to a single feature. Semantic tokens lose `KeywordTokenAnalyzer` and the legacy `collect_tokens` with their fallback.

### D2: Scope API migration is the gating prerequisite for `ScopeTree` deletion

`ScopeTree` cannot be deleted while `Namespace.find_variable`/`get_variable_matchers`/`get_resolvable_variables` call it, and the API can only use the model once every namespace has one, that is once the flag is gone. First `get_variables_at()` takes the column like `find_variable()` and keeps the precedence of `ScopeTree`, and a test compares the three API methods on `ScopeTree` and on the model, both built by the `SemanticAnalyzer`, at positions over the LSP test data. Then the API delegates to `model.find_variable` / `model.get_variables_at`, the `SemanticAnalyzer` stops calling `ScopeTreeBuilder`, `AnalyzerResult.scope_tree` and the `local_scopes` field of `NamespaceData` go, and `scope_tree.py` is deleted together with the comparison test. `get_resolvable_variables` adds a resolution step on top of `get_variables_at` — port that logic, don't drop it.

*Alternative considered*: keep a thin `ScopeTree` shim over the model — rejected; that preserves the very indirection this phase removes (no unasked infrastructure).

### D3: Order: fallbacks, flag, legacy analyzer, scope API

Remove the flag only after all fallbacks are gone — otherwise a half-removed flag leaves features branching on a setting that no longer exists. The flag goes from every place it can be set or is stored: `package.json`, `workspace_config.py`, the IntelliJ setting, the `semantic-model` option of robot.toml, the switch-off rule of `semantic-model-switchover` (its design D5) in `document_cache_helper.py`, `set_semantic_model_enabled`, the namespace cache metadata and `dump-model`; a robot.toml that still sets the option loads, and the option is ignored. Without the flag `NamespaceAnalyzer` is unreachable and goes with `ModelHelper`; only then can `AnalyzerResult.scope_tree`, which both analyzers fill, be dropped. Order: fallbacks → flag/config → delete `NamespaceAnalyzer`/`ModelHelper` → scope API → delete `scope_tree.py`. Every test that loses its reference goes in the same commit, so each commit stays green.

### D4: Comparison tests go, Level-D simplifies

Level-E tests compare against `NamespaceAnalyzer` (`test_variable_pipeline_comparison.py`, the parity halves of `test_nested_variable_resolution.py`) and benchmark relative to it (`test_analyzer_performance.py`) — meaningless once it is deleted; remove them. The same holds for the comparisons of the model path with the legacy path: `test_semantic_tokens_flag_parity.py` and the parity checks of the `test_*_model.py` suites go with their feature's fallback, `test_hover_model.py` and `test_completion_model.py` with the flag. What checks expected results of its own stays as a single-path test; the regtest snapshot suites, which run on the model path since the switchover, stay the reference. Tests parametrized over the flag (such as `test_private_keywords.py`) run once. Level-D (the flag-parametrized fixture from switchover) collapses to a single path; drop the parameterization but keep its assertions on the snapshot suites.

### D5: The helpers completion uses move into completion

Without the fallbacks, completion is the only user of `ModelHelper`. The six methods it calls (`split_bdd_prefix`, `strip_bdd_prefix`, `is_bdd_token`, `get_keyworddoc_and_token_from_position`, `get_namespace_info_from_keyword_token`, `get_argument_info_at_position`) and what they need move into `completion.py`, and `CompletionCollector` stops inheriting from `ModelHelper`.

*Alternative considered*: a shared helper module — rejected; there is no second user (no unasked infrastructure).

## Risks / Trade-offs

- [A fallback path silently did something the model path does not (an unnoticed non-parity)] → the switchover harness already asserted cross-feature parity with the flag on; deleting the proven-dead `else` cannot change default behavior. Any latent gap would already have failed switchover.
- [The model's variable lookups differ from `ScopeTree` (`get_variables_at()` compares lines only and reverses the file-scope precedence today; `get_resolvable_variables` adds a resolution step)] → the comparison test of D2 must pass on all RF versions before the API switches; port and unit-test the resolution step against the pre-change behavior.
- [Out-of-tree importers of the deleted classes break] → these are internal diagnostics classes; note the removal in the release notes. No public API guarantee covered them.
- [Whoever switched the model off gets it after this change; the setting is ignored] → intended, the model is unconditional; named in the release notes like the removal of the classes.

## Migration Plan

Ordered commits: (1) remove fallbacks per feature, each with its comparisons (several commits; semantic tokens with `KeywordTokenAnalyzer`, completion's helpers into completion), (2) remove the flag + config plumbing with the flag-parametrized tests, the hover and completion comparisons and Level-D's parameterization, (3) delete `namespace_analyzer.py` / `model_helper.py` with Level-E, (4) make `get_variables_at()` match `ScopeTree` + the comparison test, redirect the `Namespace` scope API to the model, drop `ScopeTreeBuilder` / `AnalyzerResult.scope_tree` / `local_scopes`, delete `scope_tree.py`, (5) design doc: transition passages historical, reference extracted. The main-spec deltas are written before (1). Rollback = git revert (no runtime toggle remains by design).

## Open Questions

_None._ The question whether helpers in `ModelHelper` are still needed outside the fallbacks is answered by D5.
