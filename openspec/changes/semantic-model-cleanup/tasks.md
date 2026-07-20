# Tasks: semantic-model-cleanup

## 1. Preparation

- [ ] 1.1 Verify prerequisite (HARD GATE): `semantic-model-switchover` is implemented and stable (flag defaults `true`, cross-feature parity + performance harness green, no reported regressions). Do not proceed otherwise.
- [ ] 1.2 Grep for every `namespace.semantic_model` `if/else` fallback and every `ModelHelper` / `ScopeTree` / `NamespaceAnalyzer` import; produce the deletion checklist

## 2. Remove legacy fallback paths (one feature per commit)

- [ ] 2.1 semantic_tokens, inlay_hint, signature_help — collapse to the model body, drop the `else`
- [ ] 2.2 code_action_documentation, code_action_quick_fixes, code_action_refactor — collapse; remove the `ModelHelper` mixin/import once the fallback is gone
- [ ] 2.3 hover (model branch from `semantic-model-hover`) — collapse to model-only
- [ ] 2.4 completion — collapse to model-only; remove the `ModelHelper` mixin/import
- [ ] 2.5 selection_range, inline_value, debugging_utils — collapse; remove residual `ModelHelper` usage
- [ ] 2.6 After each: the feature's `test_*_model.py` (now single-path) stays green

## 3. Migrate the Namespace scope API off ScopeTree

- [ ] 3.1 `Namespace.find_variable` → `model.find_variable`; `get_variable_matchers` → `model.get_variables_at`
- [ ] 3.2 `get_resolvable_variables` → `model.get_variables_at` + port the resolution step; unit-test it against pre-change behavior
- [ ] 3.3 Remove `ScopeTreeBuilder` usage and the `local_scopes` field from `NamespaceData`; verify `from_data()` no longer reconstructs a `ScopeTree`

## 4. Remove the flag and delete retired subsystems

- [ ] 4.1 Remove `robotcode.experimental.semanticModel` from `package.json`, `workspace_config.py`, `document_cache_helper.py`, and `set_semantic_model_enabled`
- [ ] 4.2 Delete `namespace_analyzer.py`, `model_helper.py`, `scope_tree.py`; grep-confirm no remaining importers (move any still-needed fallback-only helper to its single call site — design Open Question)
- [ ] 4.3 `hatch run lint:all` (no dead imports); confirm net removal ~3400+ LOC

## 5. Test cleanup

- [ ] 5.1 Remove Level-E: `test_variable_pipeline_comparison.py`, `test_analyzer_performance.py`, the parity halves of `test_nested_variable_resolution.py`
- [ ] 5.2 Simplify Level-D: drop the flag parameterization; keep assertions as single-path tests
- [ ] 5.3 `hatch run test:test` green (all RF versions)

## 6. Documentation

- [ ] 6.1 In `dev-docs/semantic-model.md`, mark the feature-flag / transition-period passages (Design section) historical — Phase-4 completion is tracked in OpenSpec
- [ ] 6.2 Extract the data-structure / query-API reference (NodeKind, TokenKind, node hierarchy, `SemanticModel` API, sub-token decomposition rules) from `dev-docs/semantic-model.md` into a code-adjacent `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/README.md` — this is the living reference of the shipped model and must track the code
- [ ] 6.3 Resolve the fate of `dev-docs/semantic-model.md`: trim the now-historical migration narrative (Motivation, NamespaceAnalyzer relationship, per-feature Impact, transition testing strategy, Tree-vs-flat-dicts comparison) to a short design rationale, or remove it (git history + archived changes preserve the "why"); move any remaining un-proposed ideas to a backlog
