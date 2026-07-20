# Tasks: semantic-model-call-hierarchy

## 1. Preparation

- [ ] 1.1 Confirm the SemanticModel is available and correct — soft sequencing, no hard prerequisite; recommended after `semantic-model-switchover` so `keyword_doc` / `inner_calls` / `keyword_references` are reliably populated workspace-wide (can also run flag-gated earlier)
- [ ] 1.2 Confirm the LSP call-hierarchy types in `core/lsp/types.py` cover the request/response shapes needed; note any missing field

## 2. prepareCallHierarchy

- [ ] 2.1 Add `call_hierarchy.py` protocol part; `prepare` resolves the symbol under the cursor via `model.statement_at()` / `token_path_at()` to a `DefinitionBlock` (KEYWORD/TESTCASE) or a `KeywordCallStatement.keyword_doc` pointing at a workspace definition
- [ ] 2.2 Build `CallHierarchyItem` with `data` carrying stable identity (source URI + definition range / `KeywordDoc.stable_id`) for cross-file round-trip

## 3. outgoingCalls

- [ ] 3.1 Add a reusable "statements within a definition body" helper (walks `DefinitionBlock.body`, descends `RunKeywordCallStatement.inner_calls`)
- [ ] 3.2 Emit one `CallHierarchyOutgoingCall` per resolved callee `keyword_doc`, `from_ranges` = KEYWORD token ranges (inner-call ranges for inner calls)

## 4. incomingCalls

- [ ] 4.1 Resolve the item back to a `KeywordDoc`; look up `keyword_references[keyword_doc]` across workspace models
- [ ] 4.2 Group call-site `Location`s by enclosing definition (`enclosing_definition(line)`); emit one `CallHierarchyIncomingCall` per caller; tests have no incoming calls (empty is correct)

## 5. Registration and tests

- [ ] 5.1 Declare `callHierarchyProvider` in server capabilities; wire the part into the protocol and the VS Code extension where analogous providers are registered
- [ ] 5.2 `test_call_hierarchy.py`: prepare/incoming/outgoing over plain calls, namespace-qualified, BDD-prefixed, Run Keyword inner calls, cross-file callers
- [ ] 5.3 `hatch run test:test` green (all RF versions); `hatch run lint:all`

## 6. Documentation

- [ ] 6.1 Update the Ideas section of `dev-docs/semantic-model.md` to reflect the shipped Call Hierarchy feature; add a docs/news entry for the new feature
