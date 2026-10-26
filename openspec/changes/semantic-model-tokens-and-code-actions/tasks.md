# Tasks: semantic-model-tokens-and-code-actions

## 1. Gate

- [ ] 1.1 Verify the prerequisite of groups 2 and 3 (HARD GATE, design D8). `semantic-model-cleanup` must be implemented and archived:
  - the setting `robotcode.experimental.semanticModel` no longer exists, and `namespace_analyzer.py` is deleted;
  - the main specs hold the requirements of `semantic-model-feature-tests`, such as "BDD prefixes" in `semantic-highlighting`, and the capability `code-action-refactorings`.

  Group 4 needs no gate. Do not start groups 2 and 3 otherwise.

## 2. Semantic tokens

- [ ] 2.1 ST21 (design D4): the generic token table no longer maps `Token.WITH_NAME`. Add the test of "AS of EXCEPT" to `test_semantic_tokens_rules.py`; it passes with the fix and fails without it on Robot Framework 7.0 and newer. Verify that `AS` and `WITH NAME` of Library imports keep their `settingImport` tokens.
- [ ] 2.2 ST20 (design D2): after an embedded value, continue at its end. Add the test of "Fixed text right after a value"; it passes with the fix and fails without it.
- [ ] 2.3 ST3 (design D2): from Robot Framework 7.3 on, match embedded arguments through Robot Framework's placeholders and map the spans back to the written text. Add the test of "Variable for an embedded argument with a custom pattern", and analyzer tests in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/` for a name with two variables and with an item access; they pass with the fix and fail without it on 7.3 and newer.
- [ ] 2.4 ST30 (design D5): the text of an option renders as control flow and its variables as variables. Add the tests of "Variable in an option value" and "Text and a variable in an option value"; they pass with the fix and fail without it, and the option tests of `test_semantic_tokens_variables.py` stay green.
- [ ] 2.5 ST11 (design D3): the BDD prefix comes first from Robot Framework 7.1 on. Add the tests of "Name that resolves with and without the prefix" and "Name that resolves with and without the prefix before Robot Framework 7.1". The second passes with the fix and fails without it on 7.0. Verify on 7.0 that hover and go to definition on `Given Prefixed` lead to the keyword `Given Prefixed`.
- [ ] 2.6 Run the semantic-token recordings (`test_semantic_tokens.py`) on every Robot Framework version.
  - Expected changes: the fixed text after embedded values now starts right after the value, for example in `bddstyle.robot` and `versions/rf61/embedded_keywords.robot` (ST20); `AS` of `EXCEPT` in `symbols.robot` from 7.0 on (ST21); and the options with variables in `references.robot` (ST30).
  - Explain every other difference, and on 7.0 also check the other recordings (ST11).
  - Reset the reviewed outputs with `hatch run test.<rf-env>:test-reset <path>`.

## 3. Documentation actions

- [ ] 3.1 CD3 (design D6): the prefix of a call documents its import without a keyword, and the alias of a Library import documents that import.
  - Add the tests of "Prefix of the call", "Prefix BuiltIn" and "Alias after AS" to `test_documentation_target.py`; they pass with the fix and fail without it.
  - Move the cursor of `test_prefixed_call_uses_the_arguments_of_its_import` to the keyword name, and let the `BuiltIn.Log` row of `test_keyword_in_an_inline_if_or_in_run_keyword_arguments` expect the library.
  - Verify that `test_hover_documentation_links.py` stays green.
- [ ] 3.2 CD2 (design D6): a selection inside a name gives the target, also on a call. Add the tests of the four scenarios of "Documentation actions for a selection"; "Selected keyword name" and "Selected call with a prefix" pass with the fix and fail without it.
- [ ] 3.3 Review the recordings of `test_code_action_show_documentation.py` on every version: positions at the start of a prefixed call now show the library page. Reset the reviewed outputs. Verify that the hover recordings did not change.
- [ ] 3.4 In the Documentation Viewer guide (`docs/src/content/docs/guides/vscode/documentation-viewer.mdx`, "Opening a viewer"), name the alias of a Library import and the prefix of a call, which show the page of the import from its start, and the selection inside a name. Verify the page with `npm run docs:build`.

## 4. Surround with IF, FOR, WHILE and GROUP

No gate on the cleanup. Start after the Surround fixes of `code-action-and-selection-range-fixes` (design D7).

- [ ] 4.1 Offer the four variants for the selections of the TRY variants, GROUP from Robot Framework 7.2 on, and disable FOR and WHILE for a selection with `BREAK` or `CONTINUE` (design D7). Add the tests of "Offered with the TRY variants", "GROUP before Robot Framework 7.2" and "BREAK in the selection" to `test_code_action_refactor_rules.py`; they pass with the change and fail without it.
- [ ] 4.2 Write the blocks of the four variants, with the placeholders of design D7. Add the tests of the scenarios "IF", "FOR", "WHILE" and "GROUP"; they pass with the change and fail without it.
- [ ] 4.3 Name the new variants where the guides list the Surround actions:
  - `docs/src/content/docs/guides/vscode/writing-code.mdx`;
  - `docs/src/content/docs/guides/pycharm/writing-code.mdx`;
  - `docs/src/content/docs/guides/variable-not-found.md`.

  Verify the pages with `npm run docs:build`.

## 5. Final check

- [ ] 5.1 `hatch run test:test` green on all Robot Framework versions, `hatch run lint:all` clean, and `openspec validate semantic-model-tokens-and-code-actions --strict` passes.
