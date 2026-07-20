# Tasks: semantic-model-tier1-completion

## 1. Repair the parity suite (honest red baseline)

- [ ] 1.1 Fix `_make_protocol()` in `test_semantic_tokens_flag_parity.py`: nested settings shape (`{"robotcode": {"experimental": {"semantic_model": True}}}` merged into the existing `robotcode` section) instead of the literal dotted key
- [ ] 1.2 Add the vacuity guard: flag-on fixture opens a document and asserts `namespace.semantic_model is not None` before any comparison
- [ ] 1.3 Run the suite over the full corpus and record the real gap list (expected: variable fragments, inner calls, modifiers)

## 2. Full-fidelity rendering in collect_tokens_from_model

- [ ] 2.1 Sub-token descent: emit leaf sub-tokens recursively instead of flat parents (D2); range filtering applies to leaves
- [ ] 2.2 Inner-call traversal: position-merge `inner_calls[*].tokens` with the outer token stream, inner wins on overlap, assert ascending positions (D3)
- [ ] 2.3 Modifiers: port the legacy modifier inventory from `generate_sem_sub_tokens` (builtin keyword, builtin/local/environment variables, …) onto the model renderer using `stmt.keyword_doc` / `model.find_variable()` (D4)
- [ ] 2.4 Check the embedded-keyword regex split and other "stays in the generator" visual transformations — apply the same post-processing to the model path where legacy output depends on it

## 3. Close the gap to green

- [ ] 3.1 Iterate the corpus until parity; for each remaining deviation decide fix vs. reasoned xfail (only where the model is more correct than legacy)
- [ ] 3.2 `hatch run test:test` green (all RF versions); `hatch run lint:all`

## 4. Documentation

- [ ] 4.1 Update the Semantic Tokens entry in `dev-docs/semantic-model.md` (Impact-on-LSP section) if the parity outcome changes it — the xfail set lives in the test, progress in OpenSpec
