# Tasks

## 1. Completion in the language server (D3, D6)

- [ ] 1.1 Add the part `RobotDocumentationViewerPart` in `packages/language_server/src/robotcode/language_server/robotframework/parts/documentation_viewer.py` with the request `robot/documentationViewer/completeTarget`, and register it in `robotframework/protocol.py` (D3). Add the tests of D6 in `tests/robotcode/language_server/robotframework/parts/test_documentation_viewer_target_completion.py`, on a project in `tmp_path` with `libraries/ShopLibrary.py` on the Python path and `resources/shop.resource`. Verify with `hatch run test:test tests/robotcode/language_server/robotframework/parts/test_documentation_viewer_target_completion.py` and `hatch run lint:all`.

## 2. Suggestions in the extension (D1, D4)

- [ ] 2.1 Add `LanguageClientsManager.getDocumentationTargetCompletions` in `vscode-client/extension/languageclientsmanger.ts` (D4). In `vscode-client/extension/documentationViewer.ts`, handle `suggest`:
  - the folder of the message, else the viewer's folder, else the only workspace folder, without asking;
  - the completion for a text without `::`;
  - the previous request canceled, and canceled requests not logged;
  - the answer `suggestions` (D1).

  Verify with `npm run compile` and `npm run lint`.

## 3. The suggestion list in the viewer (D1, D2, D5)

- [ ] 3.1 Add the messages `suggest` and `suggestions` and the type of a completion to `vscode-client/documentationViewer/protocol.ts`. Verify with `npm run compile`.
- [ ] 3.2 Build the list in `vscode-client/documentationViewer/app.tsx` and `viewer.css` (D1, D2): opening, the pause after typing, the keys, the mouse, inserting, and closing. Verify with `npm run compile` and `npm run lint`. In the isolated VS Code harness, on the demo project, check the scenarios:
  - of "Suggestions under the target field", except "Option+Escape on macOS", which the harness on Linux cannot run;
  - of "Completion of the target's name";
  - of "Choosing a suggestion".
- [ ] 3.3 Make the field a combobox for screen readers (D5). In the harness, check the scenario "Selected suggestion" in the accessibility tree of the viewer's page. If element reflection does not reach the tree, switch the field to the fallback of D5, and record the finding and the switch in design.md. Verify with `npm run compile` and `npm run lint`.
- [ ] 3.4 Describe the list in the section "The target field" of `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`: the completion and the keys, and that on macOS, where Ctrl+Space usually switches the input source, Option+Escape opens the list as well. Add a point to "Limits" that the completion lists every module on the Python path, as in the editor. Verify with `npm run docs:build`.

## 4. Integration checks

- [ ] 4.1 In the harness, check the scenario of "No suggestions without a language server" with a folder whose interpreter has no Robot Framework. Check that "Another target", "Target that fails" and "Back button of the toolbar" behave as before.

## Workflow follow-up

- Archive the change with its delta specs synced into `openspec/specs/vscode-documentation-viewer/spec.md` and `openspec/specs/vscode-user-guide/spec.md`.
