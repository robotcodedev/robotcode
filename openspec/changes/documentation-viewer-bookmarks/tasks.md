# Tasks

## 1. The store of bookmarks (D1, D7, D9)

- [ ] 1.1 Add the store class in `vscode-client/extension/documentationViewerBookmarks.ts` with name or file, adding, removing, the bookmarks of a folder and by group, the defaults on the first start, the reset, the keys for Settings Sync and its change event (D1, D7). Add its unit tests in `vscode-client/test/documentationViewerBookmarks.test.ts` (D9). Verify with `npm run compile`, `npm run lint` and `xvfb-run -a npm test`.

## 2. The extension (D1, D3, D6, D7)

- [ ] 2.1 Create the store on activation. In `vscode-client/extension/documentationViewer.ts`:
  - handle `bookmark`;
  - send `bookmarks` with the bookmarks of the viewer's folder after each `ready`, after a change of the store and after a viewer switches its folder;
  - add the command `robotcode.documentationBookmarks.open` (D3).

  Verify with `npm run compile` and `npm run lint`.
- [ ] 2.2 Add the view in `vscode-client/extension/documentationBookmarksView.ts` and its contributions in `package.json` (D6, D7):
  - the view with its `when`;
  - `open`, `remove` and `reset`, and the menus `view/title` and `view/item/context`;
  - `viewsWelcome`;
  - the palette entry *RobotCode: Reset Documentation Bookmarks* with its confirmation.

  Verify with `npm run compile` and `npm run lint`. In the isolated VS Code harness, check the scenarios of "The view Documentation Bookmarks", "Default bookmarks" and "Resetting the bookmarks".

## 3. Bookmarks in the viewer (D2, D3, D4, D5, D8)

- [ ] 3.1 Add the messages `bookmark` and `bookmarks` and the type of a bookmark to `vscode-client/documentationViewer/protocol.ts`. Verify with `npm run compile`.
- [ ] 3.2 Add the star after the target field in `vscode-client/documentationViewer/app.tsx`: the place at the top of the view, its state while scrolling, and its names (D2, D5). Verify with `npm run compile` and `npm run lint`. In the harness, check the scenarios of "Bookmarks of places in a viewer".
- [ ] 3.3 Add the bookmarks to the suggestion list in `app.tsx`, `suggestions.tsx` and `viewer.css` (D3, D4, D8): matching, the selection over bookmarks and completions, Enter, click and Tab, and the remove button. Verify with `npm run compile` and `npm run lint`. In the harness, check:
  - the scenarios of "Bookmarks in the suggestion list" and "Removing a bookmark in the list";
  - "Empty field", "Order of the suggestions" and "Only bookmarks without a language server";
  - "Selected suggestion" and the name of a bookmark option in the accessibility tree.
- [ ] 3.4 Describe the star, the view, the default bookmarks with their reset, the bookmarks in the list, and that Settings Sync takes the bookmarks of names along while it syncs extensions, in `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`. Verify with `npm run docs:build`.

## 4. Integration checks

- [ ] 4.1 In the harness, check the scenarios of "Where a bookmark holds", using a second workspace and a multi-root workspace. Check that "Typing a name", "Enter on the first suggestion" and "Typing on while the list is open" behave as before. "Bookmarks with Settings Sync" is covered by the unit test of the keys; Settings Sync itself is not checked.

## Workflow follow-up

- Archive the change with its delta specs synced into `openspec/specs/vscode-documentation-viewer/spec.md` (including the renamed requirement) and `openspec/specs/vscode-user-guide/spec.md`.
