# Tasks: semantic-model-hover

## 1. Preparation

- [ ] 1.1 Prerequisites are archived (`semantic-model-sidecar-cleanup`, `semantic-model-tier1-completion`); confirm the mixin is gone from `hover.py` and `PYTHON_VARIABLE_REF` is on CONDITION tokens
- [ ] 1.2 Add the missing hover positions (D3): a keyword in the body of the inline IF in `hover.robot`, the keyword of its `Run Keyword If` call, and the variable of a VAR statement (Robot Framework 7.0 and newer only)

## 2. Model branch in hover.py

- [ ] 2.1 Add `_collect_from_model()`: `token_path_at()` + `statement_at()` dispatch skeleton, branch in `collect()` on `namespace.semantic_model`
- [ ] 2.2 Variable hover: VARIABLE_BASE under VARIABLE / VARIABLE_NOT_FOUND / PARAMETER (also in assignment cells and VARIABLE_NAME) and PYTHON_VARIABLE_REF; a use via `model.find_variable(name, line, col)`, a definition by its name range (D6); the range is the VARIABLE_BASE range, the other parts of a variable give no hover; reuse the value rendering (`_my_repr`, `imports_manager.resolve_variable`)
- [ ] 2.3 Keyword hover: KEYWORD leaf → enclosing statement `keyword_doc` (legacy precedence: variable beats keyword when both match)
- [ ] 2.3a Inner-call hover: when the position falls on an ARGUMENT of a `RunKeywordCallStatement`, search `inner_calls` recursively for a KEYWORD_INNER or NAMESPACE token covering the position and hover that inner call's `keyword_doc` or `lib_entry` (legacy shows the inner doc via `keyword_references`)
- [ ] 2.3b Inline-IF hover: a keyword in the body of an inline IF, which `token_path_at()` does not find because its call is a statement of its own on the line, resolves to that call's `keyword_doc` (D5)
- [ ] 2.3c Add the model lookup of D5 (the keyword call whose keyword reference covers a position: the statement of the line, the other statements of an inline IF line, `inner_calls` recursively) and use it for 2.3a and 2.3b
- [ ] 2.4 Namespace/import hover: NAMESPACE → `stmt.lib_entry` / `ImportStatement.lib_entry`; IMPORT_NAME → import hover content
- [ ] 2.5 Test case hover: TEST_NAME → the test's RF `TestCase` node, looked up by the line of the definition; move the rendering of `hover_TestCase` into a helper both paths use (D7)
- [ ] 2.5a Keyword definition hover: KEYWORD_NAME → the keyword's `KeywordDoc` from `namespace.library_doc.keywords` by line, rendered with `_keyword_markdown`
- [ ] 2.6 Documentation target: `_target_at_from_model` in `code_action_documentation.py` uses the lookup of 2.3c, so a keyword in an inline IF body or in Run Keyword arguments gets the documentation source actions and the link in the heading of its hover on the model path too; test the targets on both paths for an inline IF, `Run Keyword` and a nested `Run Keyword If`, and remove the known-gap note from `doc-viewer-access` (`design.md`, Risks) or its archived copy

## 3. Parity tests

- [ ] 3.1 Add `test_hover_model.py`: dual-protocol (flag OFF/ON) comparison of full hover responses over all hover test positions, including the cases of `test_hover_test_metadata.py` and `test_hover_documentation_links.py`, also with viewer links on for keywords in an inline IF body and in Run Keyword arguments; document any xfail with reason
- [ ] 3.2 Run existing hover regtest suite under both flag states; `hatch run test:test` green

## 4. Granularity audit

- [ ] 4.1 Build the consumer matrix: every variable-related TokenKind × consumer (Tier 1 map, signature help, code actions, inlay hints, hover dispatch) with keep/merge verdict; append table to `dev-docs/semantic-model.md`
- [ ] 4.2 Merge zero-consumer kinds (if any) in `enums.py` / builders; all parity and snapshot suites must pass unchanged

## 5. Wrap-up

- [ ] 5.1 `hatch run lint:all` + full test matrix relevant to touched RF-version-specific paths
- [ ] 5.2 Update `dev-docs/semantic-model.md`: tick Tier 3 hover item and the granularity-audit item; note References/Rename as "no migration needed"
