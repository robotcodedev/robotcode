# Tasks: semantic-model-completion

## 1. Parity test

- [ ] 1.1 Add `tests/robotcode/language_server/robotframework/parts/test_completion_model.py` (design D2): two module-scoped protocols with the vacuity guard, the positions over the `.robot` files of the LSP test data, items compared after replacing the object ids in `data`; set the per-file cap from a measured run; verify the test runs and reports every mismatch with file, line and column
- [ ] 1.2 Add the documents of the completion tests (`test_completion_*.py`, `test_private_keywords.py`) as a temporary project opened in both protocols; verify the test reaches every document
- [ ] 1.3 Add the document with incomplete input (design D2 list) and the test of a line typed before the next analysis (spec "Completion offers items for the current text"), on both flag states; verify every typing position offers items with the flag off and the typed line offers the named arguments of `Log`
- [ ] 1.4 `dev-docs/semantic-model.md`: replace the model dispatch sketch in the Completion section with this approach (context from the current text, the namespace of the last finished analysis, parity through `test_completion_model.py`), and drop named-argument and BDD-prefix completion from the Ideas Collection; verify with `git diff` that only these passages changed

## 2. Deviations

- [ ] 2.1 Run the test on all RF versions (`hatch run test:test`) and decide every deviation per design D3: fix the SemanticAnalyzer with a regression test (passes with the fix, fails without it), or add a known deviation with its reason; verify the test is green on every RF version

## 3. Granularity audit

- [ ] 3.1 Build the consumer matrix (design D5) and append the keep/merge table to `dev-docs/semantic-model.md`; verify that every variable-related `TokenKind` has a row
- [ ] 3.2 Merge the kinds without a distinct consumer (if any) in `enums.py` and the token builders; verify `test_semantic_tokens_flag_parity.py`, the analyzer snapshots and all `test_*_model.py` suites pass unchanged

## 4. Final check

- [ ] 4.1 `hatch run test:test` and `hatch run lint:all` green
