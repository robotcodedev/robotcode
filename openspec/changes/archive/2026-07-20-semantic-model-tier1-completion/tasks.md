# Tasks: semantic-model-tier1-completion

## 1. Repair the parity suite (honest red baseline)

- [x] 1.1 Fix `_make_protocol()` in `test_semantic_tokens_flag_parity.py`: nested settings shape (`{"robotcode": {"experimental": {"semantic_model": True}}}` merged into the existing `robotcode` section) instead of the literal dotted key
- [x] 1.2 Add the vacuity guard: flag-on fixture opens a document and asserts `namespace.semantic_model is not None` before any comparison
- [x] 1.3 Run the suite over the full corpus and record the real gap list (see `gap-list.md`)

## 2. Model carries final render semantics (D6)

- [x] 2.1 Analyzer correctness fixes from the red phase: `Run Keywords`/`Run Keyword If` decomposition on the REGISTERED path, `[Setup] NONE`/empty `[Teardown]` statements, `Token.SUITE_NAME` mapping
- [x] 2.2 Token model: `TokenModifier` enum + `SemanticToken.modifiers`; refined TokenKinds (`OPERATOR`, `SETTING_IMPORT`, `HEADER_*`, `FOR_SEPARATOR`, `VAR_MARKER`, `OPTION`, `OPTION_NAME`/`OPTION_VALUE`, `PARAMETER`, `KEYWORD_INNER`)
- [x] 2.3 Analyzer emits final leaf tokens: header kinds, keyword builtin modifiers + embedded splits, definition-name variable splits, bracket-setting splits, named-argument `=` operators, import kinds (setting word, path fragments, alias, validated named args), option kinds (VAR/FOR whole vs. WHILE/EXCEPT triple), `[Arguments]` kinds, Variables-section value decomposition + dict items, run-keyword ELSE/AND control-flow marking, unresolved-template `ARGUMENT` kind

## 3. Renderer strip-down (D7)

- [x] 3.1 `collect_tokens_from_model()` = leaf descent + static kind/modifier tables + declarative emission policy + BDD-gap compat rule + inner-call position merge; remove `RF_VERSION`, re-tokenization, value parsing, and semantic `isinstance` checks from the model path

## 4. Close the gap to green

- [x] 4.1 Iterate the corpus until parity on all RF versions; document remaining deviations as reasoned (version-scoped where needed) xfails — only where the model is more correct than legacy
- [x] 4.2 Update semantic-analyzer unit tests for the refined token shape
- [x] 4.3 `hatch run test:test` green (all RF versions); `hatch run lint:all`

## 5. Documentation

- [x] 5.1 Update the Semantic Tokens entry in `dev-docs/semantic-model.md` (Impact-on-LSP section) if the parity outcome changes it — the xfail set lives in the test, progress in OpenSpec
