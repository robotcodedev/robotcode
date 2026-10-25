# Tasks

## 1. The store of bookmarks (D1, D7, D9)

- [x] 1.1 Add the store class in `vscode-client/extension/documentationViewerBookmarks.ts` with the groups All Workspaces and of the workspace folders, the bookmarks that hold for a folder, adding to a group, removing from a group and removing a place from what holds for a folder, moving between groups, the defaults on the first start, the reset, the keys for Settings Sync and its change event (D1, D7). Add its unit tests in `vscode-client/test/documentationViewerBookmarks.test.ts` (D9). Verify with `npm run compile`, `npm run lint` and `xvfb-run -a npm test`.

## 2. The extension (D1, D3, D6, D7)

- [x] 2.1 Create the store on activation. In `vscode-client/extension/documentationViewer.ts`:
  - handle `bookmark`: add into the viewer's folder, remove the place from the folder and from All Workspaces;
  - send `bookmarks` with the bookmarks of the viewer's folder after each `ready`, after a change of the store and after a viewer switches its folder;
  - add the command `robotcode.documentationBookmarks.open` (D3).

  Verify with `npm run compile` and `npm run lint`.
- [x] 2.2 Add the view in `vscode-client/extension/documentationBookmarksView.ts` and its contributions in `package.json` (D6, D7):
  - the view with its `when`, and its groups while a bookmark exists;
  - `open`, `remove`, `moveToAllWorkspaces`, `moveToFolder` and `reset`, and the menus `view/title` and `view/item/context`;
  - moving by drag and drop;
  - `viewsWelcome`;
  - the palette entry *RobotCode: Reset Documentation Bookmarks* with its confirmation.

  Verify with `npm run compile` and `npm run lint`. In the isolated VS Code harness, check the scenarios of "The view Documentation Bookmarks", "Moving a bookmark", "Default bookmarks" and "Resetting the bookmarks".

## 3. Bookmarks in the viewer (D2, D3, D4, D5, D8)

- [x] 3.1 Add the messages `bookmark` and `bookmarks` and the type of a bookmark to `vscode-client/documentationViewer/protocol.ts`. Verify with `npm run compile`.
- [x] 3.2 Add the star after the target field in `vscode-client/documentationViewer/app.tsx`: the place at the top of the view, its state while scrolling, and its names (D2, D5). Verify with `npm run compile` and `npm run lint`. In the harness, check the scenarios of "Bookmarks of places in a viewer".
- [x] 3.3 Add the bookmarks to the suggestion list in `app.tsx`, `suggestions.tsx` and `viewer.css` (D3, D4, D8): matching, the selection over bookmarks and completions, Enter, click and Tab, and the remove button. Verify with `npm run compile` and `npm run lint`. In the harness, check:
  - the scenarios of "Bookmarks in the suggestion list" and "Removing a bookmark in the list";
  - "Empty field", "Order of the suggestions" and "Only bookmarks without a language server";
  - "Selected suggestion" and the name of a bookmark option in the accessibility tree.
- [x] 3.4 Describe the star, the view with its groups and moving bookmarks, the default bookmarks with their reset, the bookmarks in the list, and that Settings Sync takes All Workspaces along while it syncs extensions, in `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`. Verify with `npm run docs:build`.

## 4. Integration checks

- [x] 4.1 In the harness, check the scenarios of "Bookmarks of places in a viewer" and "Where a bookmark holds" again, using a second workspace and a multi-root workspace, and "Removing a bookmark in the list" for a bookmark of All Workspaces. Check that "Typing a name", "Enter on the first suggestion" and "Typing on while the list is open" behave as before. "Bookmarks with Settings Sync" is covered by the unit test of the keys; Settings Sync itself is not checked.

## 5. The place in the target field (D10)

- [x] 5.1 In `vscode-client/documentationViewer/app.tsx`: the text of the target field with the place, the place of an entered text after its last `#`, the refresh and the new entry for the target shown, the names of keywords and data types as places, Tab on a bookmark and the matching of bookmarks by that text (D10). Verify with `npm run compile` and `npm run lint`. In the harness, check the scenarios of "The place in the target field" and "Tab on a bookmark", and that "Another target", "Target that fails" and "Same heading again" behave as before.
- [x] 5.2 Describe the place in the target field in `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`. Verify with `npm run docs:build`.
- [x] 5.3 Let the page scroll past its end in `vscode-client/documentationViewer/viewer.css` (D2). Verify with `npm run compile`. In the harness, check the scenarios of "Scrolling past the end of a page".

## Workflow follow-up

- Archive the change with its delta specs synced into `openspec/specs/vscode-documentation-viewer/spec.md` (including the renamed requirement) and `openspec/specs/vscode-user-guide/spec.md`.
