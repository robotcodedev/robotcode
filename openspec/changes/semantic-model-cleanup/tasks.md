# Tasks: semantic-model-cleanup

## 1. Preparation

- [ ] 1.1 Verify prerequisite (HARD GATE): `semantic-model-switchover` and `semantic-model-completion` are implemented and archived, and the switchover is stable (flag defaults `true`, cross-feature parity + performance harness green, no reported regressions). Do not proceed otherwise.
- [ ] 1.2 Grep for every `namespace.semantic_model` `if/else` fallback and every `ModelHelper` / `ScopeTree` / `NamespaceAnalyzer` / `KeywordTokenAnalyzer` import and use; produce the deletion checklist and confirm that only completion uses `ModelHelper` outside the fallbacks (design D5)
- [ ] 1.3 Grep the main specs for both analysis paths, the legacy path and the flag, and write their deltas under `specs/`: REMOVED for requirements that only compare the two paths, MODIFIED for behavior stated on both paths or with and without the flag (known: the proposal's list); `openspec validate semantic-model-cleanup --strict`

## 2. Remove legacy fallback paths (one feature per commit)

- [ ] 2.1 semantic_tokens — collapse to the model body, drop the `else`, delete `KeywordTokenAnalyzer` and the legacy `collect_tokens`; inlay_hint, signature_help — collapse, drop the `else`
- [ ] 2.2 code_action_documentation, code_action_quick_fixes, code_action_refactor — collapse; remove the `ModelHelper` mixin/import once the fallback is gone
- [ ] 2.3 completion — no fallback to collapse; move the six `ModelHelper` methods it calls, and what they need, into `completion.py` (design D5) and drop the mixin; the completion tests stay green unchanged
- [ ] 2.4 selection_range, inline_value, debugging_utils — collapse; remove residual `ModelHelper` usage
- [ ] 2.5 Each of these commits removes the feature's comparisons with the legacy path (`test_semantic_tokens_flag_parity.py` with semantic tokens, the parity checks of its `test_*_model.py`) and keeps the rest of its tests green (design D4)

## 3. Remove the flag

- [ ] 3.1 Remove the flag from every place of design D3; in the same commit drop the flag parameterization of the Level-D fixture and of the flag-parametrized tests, and remove `test_hover_model.py` and `test_completion_model.py` (checks of expected results of their own stay as single-path tests)
- [ ] 3.2 Test that a robot.toml with `semantic-model = false` loads and the SemanticModel is used; regenerate `etc/robot.toml.json` and the reference pages (`hatch run create-json-schema`, `hatch run create-config-docs`, `hatch run create-vscode-settings-docs`)

## 4. Delete the legacy analyzer

- [ ] 4.1 Delete `namespace_analyzer.py` and `model_helper.py`, and with them the Level-E tests (`test_variable_pipeline_comparison.py`, `test_analyzer_performance.py`, the parity halves of `test_nested_variable_resolution.py`); grep-confirm no remaining importers

## 5. Migrate the Namespace scope API off ScopeTree

- [ ] 5.1 `SemanticModel.get_variables_at()` takes the column like `find_variable()` and keeps the precedence of `ScopeTree` (local, command line, own, imported, built-in); add the comparison test of design D2 (`find_variable`, `get_variable_matchers`, `get_resolvable_variables` on `ScopeTree` and on the model at positions over the LSP test data); verify it is green on all RF versions
- [ ] 5.2 `Namespace.find_variable` → `model.find_variable`; `get_variable_matchers` → `model.get_variables_at`
- [ ] 5.3 `get_resolvable_variables` → `model.get_variables_at` + port the resolution step; unit-test it against pre-change behavior
- [ ] 5.4 The `SemanticAnalyzer` stops calling `ScopeTreeBuilder`; remove `AnalyzerResult.scope_tree` and the `local_scopes` field from `NamespaceData`; verify `from_data()` no longer reconstructs a `ScopeTree`; delete `scope_tree.py` and the comparison test of 5.1

## 6. Final check

- [ ] 6.1 `hatch run lint:all` (no dead imports); `(cd intellij-client && ./gradlew test)`; `hatch run test:test` green (all RF versions)

## 7. Documentation

- [ ] 7.1 In `dev-docs/semantic-model.md`, mark the feature-flag / transition-period passages (Design section) historical — Phase-4 completion is tracked in OpenSpec
- [ ] 7.2 Extract the data-structure / query-API reference (NodeKind, TokenKind, node hierarchy, `SemanticModel` API, sub-token decomposition rules) from `dev-docs/semantic-model.md` into a code-adjacent `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/README.md` — this is the living reference of the shipped model and must track the code
- [ ] 7.3 Resolve the fate of `dev-docs/semantic-model.md`: trim the now-historical migration narrative (Motivation, NamespaceAnalyzer relationship, per-feature Impact, transition testing strategy, Tree-vs-flat-dicts comparison) to a short design rationale, or remove it (git history + archived changes preserve the "why"); move any remaining un-proposed ideas to a backlog
