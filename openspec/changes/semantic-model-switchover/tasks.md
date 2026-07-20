# Tasks: semantic-model-switchover

## 1. Verification harness (flag stays false)

- [ ] 1.1 Verify prerequisites (HARD GATE): `semantic-model-tier1-completion`, `semantic-model-sidecar-cleanup`, `semantic-model-hover`, `semantic-model-completion` are all implemented (every LSP feature has a proven model path). Do not proceed otherwise.
- [ ] 1.2 Build the global Level-D fixture: parametrize the existing LSP snapshot/regtest suites over `semantic_model` OFF/ON (generalize the `test_semantic_tokens_flag_parity.py` dual-protocol pattern); assert identical output across all migrated features; vacuity guard on the flag-on protocol
- [ ] 1.3 Add `test_analyzer_performance.py` (Level E): overhead ≤ 30% (`SemanticAnalyzer` vs `NamespaceAnalyzer`, warmup + N runs), model ≤ 500 KB/file (pickle-size estimate), pickle round-trip + `resolve_references()` ≤ 50 ms/file
- [ ] 1.4 Both harness suites green on all RF versions with the flag toggled per-run

## 2. Switch the default

- [ ] 2.1 Flip `robotcode.experimental.semanticModel` default to `true` in `package.json` and `packages/robot/.../workspace_config.py`
- [ ] 2.2 `Namespace` runs `SemanticAnalyzer.run()` as the sole analyzer (verify `document_cache_helper.py` selection path); confirm no dual-analyzer overhead
- [ ] 2.3 Full LSP suite green with the flag defaulting on

## 3. Remove KeywordTokenAnalyzer

- [ ] 3.1 Delete the `KeywordTokenAnalyzer` class and its instantiation in `semantic_tokens.py`; remove the legacy semantic-tokens fallback (the model renderer is now the sole path); Tier-1 parity suite must stay green
- [ ] 3.2 `hatch run lint:all` (dead imports/helpers removed)

## 4. Variable type modifiers (new capability)

- [ ] 4.1 Emit local/global/builtin/environment modifier bits in `collect_tokens_from_model()` from `model.find_variable(value, line)` variable types
- [ ] 4.2 Targeted test for the new modifiers; reconcile with the Level-D fixture (modifiers are the sanctioned deviation from legacy output — assert accordingly)

## 5. Wrap-up

- [ ] 5.1 `hatch run test:test` green (all RF versions); `hatch run lint:all`
- [ ] 5.2 Update `dev-docs/semantic-model.md` (Impact / Ideas sections) if affected — Phase-3 completion is tracked in OpenSpec, not in the doc
