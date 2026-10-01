# Tasks: semantic-model-token-rendering

## 1. Prerequisite

- [ ] 1.1 Hard gate (design D1): verify that `semantic-model-cleanup` is implemented:
  - the setting `robotcode.experimental.semanticModel` no longer exists;
  - `namespace_analyzer.py` and `model_helper.py` are deleted;
  - `test_semantic_tokens_flag_parity.py` and the comparison tests are gone.

  If any of this is not the case, stop and report.

## 2. Grammar coverage of variables

- [ ] 2.1 Build the inventory of variable forms from the variable chapters of the Robot Framework user guide (list in design D5). Write it as a probe corpus outside the repository, one form per line, including the forms of the first probe. Verify that every form of the D5 list appears in the corpus.
- [ ] 2.2 Tokenize the corpus with a throwaway vscode-textmate/vscode-oniguruma probe against `syntaxes/robotframework.tmLanguage.json`. Record in a table in design D5, for each form, which parts the grammar tells apart: prefix and braces, name, item brackets, type hint, default value, pattern.
- [ ] 2.3 For each gap, decide between a grammar fix and a semantic token by the rule in design D5, and record the decision in D5.
- [ ] 2.4 Fix the gaps decided as grammar fixes in `syntaxes/robotframework.tmLanguage.template.json`. These include at least the `%{HOME} and …` bug, item access in usages and `[Arguments]` defaults. Then:
  - regenerate with `hatch run generate-tmlanguage`;
  - apply the same fixes to `syntaxes/robotframework-repl.tmLanguage.json` wherever it has the same rules.

  Verify:
  - the probe tells the parts apart for every form decided as a grammar fix;
  - the spec scenarios "Environment variable followed by more text" and "Item access in an argument" hold, and "Type hint" too if type hints were decided as a grammar fix.

## 3. Analyzer: name sub-tokens at every site

- [ ] 3.1 Declarations in `*** Variables ***` get variable sub-tokens (design D4). Verify with model tests: `${SCALAR}`, `@{LIST}`, `&{DICT}` and `${X} =` each contain a `VARIABLE_BASE` leaf for the name.
- [ ] 3.2 Keyword-call assignments get sub-tokens, including index and assignment mark: `${result}=`, `${a}    ${b}=`, `${DICT}[key]=`, `${DICT}[${k}]=`. Verify with model tests.
- [ ] 3.3 `[Arguments]` parameters get sub-tokens: `${arg}`, `${opt}=default`, `@{varargs}`, `&{kwargs}` and typed parameters. Verify with model tests.
- [ ] 3.4 Item access in usages produces index sub-tokens instead of a `TEXT_FRAGMENT`, following Robot Framework's item rules, including escaped brackets. Cases: `${LIST}[0]`, `${DICT}[key][sub]`, `${DICT}[${k}]`, `@{LIST}[1:]`. Verify with variable-tokenizer tests.
- [ ] 3.5 Check embedded arguments in keyword names and calls, and add sub-tokens where they are missing. Verify with a model test.
- [ ] 3.6 Run the analyzer snapshot regression tests (`tests/robotcode/robot/diagnostics/test_semantic_analyzer/test_analyzer_snapshot.py`). Review the diff: only the sub-tokens added in 3.1–3.5 may differ. Then reset the outputs with `hatch run test:test-reset <path>`.

## 4. Rendering

- [ ] 4.1 Variables render their name only (design D3):
  - remove `VARIABLE`, `VARIABLE_NOT_FOUND` and `VARIABLE_NAME` from `_ATOMIC_KINDS`;
  - render `VARIABLE_BASE` leaves with the kind and modifiers of the parent variable;
  - skip the delimiter, default, pattern, extended and inline-expression leaves;
  - handle type hints as decided in 2.3.

  Verify with unit tests for every scenario of the spec requirement "Variables get a token for their name only".
- [ ] 4.2 Stop sending comment tokens (design D2). Verify the spec scenario "Documentation and comments".
- [ ] 4.3 Remove the BDD separator token and the code that only serves it (design D6). Verify the scenarios "Step with a BDD prefix" and "Setup with a BDD prefix".
- [ ] 4.4 For each category in the "to review" table of design D2:
  - decide it against the criterion;
  - record the decision and its reason in D2;
  - implement it;
  - update the spec of this change if observable behavior changes beyond what it states.

  Verify that the D2 table has no category left without a decision.
- [ ] 4.5 Check the rendering against the spec requirement "Rendering makes no semantic decisions of its own". Verify that `grep -n "RF_VERSION" packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py` finds nothing in the rendering code, and that no new value parsing or classification by statement type was added there.

## 5. Documentation

- [ ] 5.1 Update the semantic-token section of `dev-docs/semantic-model.md`, or its successor if the cleanup has already moved it. Describe the principle and the variable rendering, and remove the legacy-compat emission policy and the "BDD-gap quirk". Verify that `grep -rn "BDD-gap\|legacy-compat" dev-docs/` finds nothing in the semantic-token description.

## 6. Verification

- [ ] 6.1 Run the semantic-token regression tests (`tests/robotcode/language_server/robotframework/parts/test_semantic_tokens.py`). Review the diff against the list of expected changes in design D8, and look at every other difference. Then reset the outputs with `hatch run test:test-reset <path>`.
- [ ] 6.2 Run `hatch run test:test` and `hatch run lint:all`, and verify that both pass.
- [ ] 6.3 Check by hand in VS Code and in IntelliJ (`runIde`), with a file covering the spec scenarios. Verify:
  - variable braces keep the grammar look when semantic tokens arrive;
  - variable names get their semantic color and modifiers;
  - comments and the space after BDD prefixes are not changed by semantic highlighting;
  - the grammar fixes from 2.4 show in both IDEs.
