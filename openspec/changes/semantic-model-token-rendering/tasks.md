# Tasks: semantic-model-token-rendering

## 1. Prerequisite

- [ ] 1.1 Hard gate (design D1): verify that `semantic-model-cleanup` and `semantic-tokens-variable-names` are implemented:
  - the setting `robotcode.experimental.semanticModel` no longer exists;
  - `namespace_analyzer.py` and `model_helper.py` are deleted;
  - `test_semantic_tokens_flag_parity.py` and the comparison tests are gone;
  - `VARIABLE`, `VARIABLE_NOT_FOUND` and `VARIABLE_NAME` are no longer in `_ATOMIC_KINDS`.

  If any of this is not the case, stop and report.

## 2. Rendering

- [ ] 2.1 Stop sending comment tokens (design D2). Verify the spec scenario "Documentation and comments".
- [ ] 2.2 Remove the BDD separator token and the code that only serves it (design D3). Verify the scenarios "Step with a BDD prefix" and "Setup with a BDD prefix".
- [ ] 2.3 For each category in the "to review" table of design D2:
  - decide it against the criterion;
  - record the decision and its reason in D2;
  - implement it;
  - update the spec of this change if observable behavior changes beyond what it states.

  Verify that the D2 table has no category left without a decision.
- [ ] 2.4 Check the rendering against the spec requirement "Rendering makes no semantic decisions of its own". Verify that `grep -n "RF_VERSION" packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py` finds nothing in the rendering code, and that no new value parsing or classification by statement type was added there.

## 3. Documentation

- [ ] 3.1 Update the semantic-token section of `dev-docs/semantic-model.md`, or its successor if the cleanup has already moved it. Describe the principle, and remove the legacy-compat emission policy and the "BDD-gap quirk". Verify that `grep -rn "BDD-gap\|legacy-compat" dev-docs/` finds nothing in the semantic-token description.

## 4. Verification

- [ ] 4.1 Run the semantic-token regression tests (`tests/robotcode/language_server/robotframework/parts/test_semantic_tokens.py`). Review the diff against the list of expected changes in design D5, and look at every other difference. Then reset the outputs with `hatch run test:test-reset <path>`.
- [ ] 4.2 Run `hatch run test:test` and `hatch run lint:all`, and verify that both pass.
- [ ] 4.3 Check by hand in VS Code and in IntelliJ (`runIde`), with a file covering the spec scenarios. Verify that comments and the space after BDD prefixes are not changed by semantic highlighting.
