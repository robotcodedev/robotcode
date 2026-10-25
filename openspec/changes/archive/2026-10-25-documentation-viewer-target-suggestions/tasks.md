# Tasks

## 1. Completion in the language server (D3, D6)

- [x] 1.1 Add the part `RobotDocumentationViewerPart` in `packages/language_server/src/robotcode/language_server/robotframework/parts/documentation_viewer.py` with the request `robot/documentationViewer/completeTarget`, and register it in `robotframework/protocol.py` (D3). Add the tests of D6 in `tests/robotcode/language_server/robotframework/parts/test_documentation_viewer_target_completion.py`, on a project in `tmp_path` with `libraries/ShopLibrary.py` on the Python path and `resources/shop.resource`. Verify with `hatch run test:test tests/robotcode/language_server/robotframework/parts/test_documentation_viewer_target_completion.py` and `hatch run lint:all`.

## 2. Suggestions in the extension (D1, D4)

- [x] 2.1 Add `LanguageClientsManager.getDocumentationTargetCompletions` in `vscode-client/extension/languageclientsmanger.ts` (D4). In `vscode-client/extension/documentationViewer.ts`, handle `suggest`:
  - the folder of the message, else the viewer's folder, else the only workspace folder, without asking;
  - the completion for a text without `::`;
  - the previous request canceled, and canceled requests not logged;
  - the answer `suggestions` (D1).

  Verify with `npm run compile` and `npm run lint`.

## 3. The suggestion list in the viewer (D1, D2, D5)

- [x] 3.1 Add the messages `suggest` and `suggestions` and the type of a completion to `vscode-client/documentationViewer/protocol.ts`. Verify with `npm run compile`.
- [x] 3.2 Build the list in `vscode-client/documentationViewer/app.tsx` and `viewer.css` (D1, D2): opening, the pause after typing, the keys, the mouse, inserting, and closing. Verify with `npm run compile` and `npm run lint`. In the isolated VS Code harness, on the demo project, check the scenarios:
  - of "Suggestions under the target field", except "Option+Escape on macOS", which the harness on Linux cannot run;
  - of "Completion of the target's name";
  - of "Choosing a suggestion".
- [x] 3.3 Make the field a combobox for screen readers (D5). In the harness, check the scenario "Selected suggestion" in the accessibility tree of the viewer's page. If element reflection does not reach the tree, switch the field to the fallback of D5, and record the finding and the switch in design.md. Verify with `npm run compile` and `npm run lint`.
- [x] 3.4 Describe the list in the section "The target field" of `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`: the completion and the keys, and that on macOS, where Ctrl+Space usually switches the input source, Option+Escape opens the list as well. Add a point to "Limits" that the completion lists every module on the Python path, as in the editor. Verify with `npm run docs:build`.

## 4. Integration checks

- [x] 4.1 In the harness, check the scenario of "No suggestions without a language server" with a folder whose interpreter has no Robot Framework. Check that "Another target", "Target that fails" and "Back button of the toolbar" behave as before.

## 5. Order and selection as in the editor (D1, D3, D6)

- [x] 5.1 Order the completions in `documentation_viewer.py` as D3 says, and add the tests of the order for `Coll` and `xml` to `test_documentation_viewer_target_completion.py` (D6). Verify with `hatch run test:test tests/robotcode/language_server/robotframework/parts/test_documentation_viewer_target_completion.py` and `hatch run lint:all`.
- [x] 5.2 Select the first suggestion when the list opens and with each new answer, in `vscode-client/documentationViewer/app.tsx` (D1). Verify with `npm run compile` and `npm run lint`. In the harness, check the scenarios of "Order of the suggestions" and "Choosing a suggestion", and "Selected suggestion" in the accessibility tree.
- [x] 5.3 In the section "The target field" of `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`, say that the first suggestion is selected, and that Enter loads the typed text after Escape. Verify with `npm run docs:build`.

## 6. Findings of the review (D1, D3, D4, D5, D6)

- [x] 6.1 In `documentation_viewer.py`, add `BuiltIn` at the top level, give no completion for dots only, count `start` in UTF-16 code units, and run the two sides apart (D3). Add the tests of D6 for `BuiltIn`, `.`, `..` and `📁docs`. Verify with `hatch run test:test tests/robotcode/language_server/robotframework/parts/test_documentation_viewer_target_completion.py` and `hatch run lint:all`.
- [x] 6.2 In `languageclientsmanger.ts`, ask only a client that runs (D4). Verify with `npm run compile` and `npm run lint`.
- [x] 6.3 In `app.tsx`, `suggestions.tsx` and `viewer.css`, keep the list to the typed text, cancel a pending request on Escape, close the list when the viewer leaves its entry, scroll the list without `scrollIntoView`, leave keys of an IME composition alone, and find the list by a ref with the classes `target-suggestions` and `target-suggestion` (D1, D5). Verify with `npm run compile` and `npm run lint`. In the harness, check:
  - the scenarios "Escape before the list appears", "Back to the same page", "BuiltIn", "Dots only" and "Typing on while the list is open";
  - that Down past the visible rows of a long list scrolls only the list;
  - "Selected suggestion" in the accessibility tree.
- [x] 6.4 In the section "The target field" of the guide, say that the list stays closed while RobotCode waits for the folder's Python environment and when it is switched off for the folder. Verify with `npm run docs:build`.

## Workflow follow-up

- Archive the change with its delta specs synced into `openspec/specs/vscode-documentation-viewer/spec.md` and `openspec/specs/vscode-user-guide/spec.md`.
