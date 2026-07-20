# Tasks: semantic-model-hover

## 1. Preparation

- [ ] 1.1 Verify prerequisite: `semantic-model-sidecar-cleanup` is implemented (mixin gone from `hover.py`, `PYTHON_VARIABLE_REF` rendered on CONDITION tokens)
- [ ] 1.2 Check hover test data coverage against the dispatch table (KEYWORD, NAMESPACE, VARIABLE forms, TEST_NAME/KEYWORD_NAME, IMPORT_NAME); extend `hover.robot` test data minimally where a dispatch row has no position

## 2. Model branch in hover.py

- [ ] 2.1 Add `_collect_from_model()`: `token_path_at()` + `statement_at()` dispatch skeleton, branch in `collect()` on `namespace.semantic_model`
- [ ] 2.2 Variable hover: VARIABLE / VARIABLE_NOT_FOUND / VARIABLE_BASE / PYTHON_VARIABLE_REF → `model.find_variable()` + existing value-resolution rendering (reuse `_my_repr`, `imports_manager.resolve_variable`)
- [ ] 2.3 Keyword hover: KEYWORD leaf → enclosing statement `keyword_doc` (legacy precedence: variable beats keyword when both match)
- [ ] 2.3a Inner-call hover: when the position falls on an ARGUMENT of a `RunKeywordCallStatement`, search `inner_calls` recursively for a KEYWORD token covering the position and hover that inner call's `keyword_doc` (legacy shows the inner doc via `keyword_references`); add `Run Keyword If` positions to the test data if missing
- [ ] 2.4 Namespace/import hover: NAMESPACE → `stmt.lib_entry` / `ImportStatement.lib_entry`; IMPORT_NAME → import hover content
- [ ] 2.5 Definition hover: TEST_NAME / KEYWORD_NAME tokens replace the `hover_TestCase` AST handler on the model path

## 3. Parity tests

- [ ] 3.1 Add `test_hover_model.py`: dual-protocol (flag OFF/ON) comparison of full hover responses over all hover test positions; document any xfail with reason
- [ ] 3.2 Run existing hover regtest suite under both flag states; `hatch run test:test` green

## 4. Granularity audit

- [ ] 4.1 Build the consumer matrix: every variable-related TokenKind × consumer (Tier 1 map, signature help, code actions, inlay hints, hover dispatch) with keep/merge verdict; append table to `dev-docs/semantic-model.md`
- [ ] 4.2 Merge zero-consumer kinds (if any) in `enums.py` / builders; all parity and snapshot suites must pass unchanged

## 5. Wrap-up

- [ ] 5.1 `hatch run lint:all` + full test matrix relevant to touched RF-version-specific paths
- [ ] 5.2 Update `dev-docs/semantic-model.md`: tick Tier 3 hover item and the granularity-audit item; note References/Rename as "no migration needed"
