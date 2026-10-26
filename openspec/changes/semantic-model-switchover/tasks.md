# Tasks: semantic-model-switchover

## 1. Verification harness (flag stays false)

- [ ] 1.1 Verify prerequisites (HARD GATE): `semantic-model-completion` is implemented, and `semantic-model-tier1-completion`, `semantic-model-sidecar-cleanup`, `semantic-model-hover` and `semantic-tokens-variable-names` are archived (every migrated feature has a proven model path; hover reads the references and completion the namespace and the current text on both paths, covered by `test_hover_model.py` and `test_completion_model.py`). Do not proceed otherwise.
- [ ] 1.2 Build the global Level-D fixture: parametrize the existing LSP snapshot/regtest suites over `semantic_model` OFF/ON (generalize the `test_semantic_tokens_flag_parity.py` dual-protocol pattern); assert identical output across all LSP features; vacuity guard on the flag-on protocol; the flag-off protocol sets the flag `false` explicitly
- [ ] 1.3 Add `test_analyzer_performance.py` (Level E): overhead ≤ 30% (`SemanticAnalyzer` vs `NamespaceAnalyzer`, warmup + N runs), model ≤ 500 KB/file (pickle-size estimate), pickle round-trip + `resolve_references()` ≤ 50 ms/file
- [ ] 1.4 Both harness suites green on all RF versions with the flag toggled per-run

## 2. Switch the default

- [ ] 2.1 Flip the default to `true` in `package.json`, `packages/robot/.../workspace_config.py` and the IntelliJ settings (`intellij-client/.../configuration/`), and let an unset `semantic-model` in robot.toml count as `true` (`packages/analyze/.../config.py`)
- [ ] 2.2 A `false` in robot.toml or in the editor setting switches the model off (design D5, `document_cache_helper.py`); test the default and both places, in the language server and with `robotcode analyze code`
- [ ] 2.3 Describe the default and how to switch the model off in `package.json`, the `semantic-model` option and the IntelliJ setting comment; regenerate `etc/robot.toml.json` and the reference pages with `hatch run create-json-schema`, `hatch run create-vscode-settings-docs` and `hatch run create-config-docs`
- [ ] 2.4 Set the flag `false` explicitly wherever a test wants the legacy path (the dual-protocol and flag-parametrized tests get it from the default today); full LSP suite green with the flag defaulting on

## 3. Builtin modifier for variables (new capability)

- [ ] 3.1 Set `TokenModifier.BUILTIN` in the analyzer on variable tokens that resolve to built-in variables, and map it to `builtin` on the name token in `collect_tokens_from_model()` (design D4); verify with `dump-model` that `${CURDIR}` carries the modifier and a `FOR` loop variable does not
- [ ] 3.2 Targeted test for every scenario of the spec `semantic-model-variable-modifiers`; the Level-D fixture, `test_semantic_tokens_flag_parity.py` and the other tests that compare the semantic tokens of both paths ignore the modifier bit on variable tokens (spec `semantic-model-tier1-parity`); update the semantic-tokens snapshots and check that only the builtin modifier on built-in variables changed

## 4. Wrap-up

- [ ] 4.1 `hatch run test:test` green (all RF versions); `hatch run lint:all`; `(cd intellij-client && ./gradlew test)`
- [ ] 4.2 `dev-docs/semantic-model.md`: the Transition Period table shows `true` as the default and that a `false` switches the model off; the Impact / Ideas sections if affected — Phase-3 completion is tracked in OpenSpec, not in the doc
