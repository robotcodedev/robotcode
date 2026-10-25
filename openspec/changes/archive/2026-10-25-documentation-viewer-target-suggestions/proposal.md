# Proposal

## Why

The target field of the Documentation Viewer takes a library, resource or suite file only as typed text: a user has to know the exact name or path and type it out. In the editor, RobotCode already completes the names of `Library` and `Resource` imports, and its language server has everything needed for this.

## What Changes

- **A suggestion list under the target field.** While the user types, after Ctrl+Space (on macOS also Option+Escape, as in the editor), or after Down, the list shows the completion of the name. An empty field shows no list. The list leaves room before the completions for bookmarks, which a separate change plans.
- **Completion of the name.** The part before the first `::` is completed as in `Library` and `Resource` imports in the editor, one level at a time:
  - modules on the Python path and the standard libraries;
  - library, resource and suite files and directories, relative to the workspace folder or absolute.
- **Order, as in the editor.** First the names that continue the typed text in the same case, then the others, each alphabetically. Of two equal names, a module comes before a file and a file before a directory. `Coll` offers `Collections` first, `xml` the Python package `xml`.
- **Keys and mouse, as in the editor.**
  - When the list opens, its first suggestion is selected; Up and Down select another.
  - Enter loads the selected suggestion. On a directory it only inserts it and shows the next level.
  - Tab inserts the selected suggestion without loading it, and Escape closes the list.
  - A click works like Enter.
  - With the list closed, as after Escape, Enter loads the typed text, as before.
- **Without a language server** for the folder, as before its Python environment is usable or when RobotCode is switched off for it, the list stays closed. The viewer starts no language server for it.
- **Screen readers** hear the field as a combobox with a list of suggestions, and the selected suggestion with its kind.
- The VS Code guide describes the list in the section about the target field.

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-documentation-viewer`: the suggestion list of the target field, the completion of the name, and the keys of the list.
- `vscode-user-guide`: the page Documentation Viewer explains the suggestions of the target field.

## Impact

- **Language server:** a new request for the completion of a target in a workspace folder, in a new part `packages/language_server/src/robotcode/language_server/robotframework/parts/documentation_viewer.py`, registered in `robotframework/protocol.py`. It uses `complete_library_import` and `complete_resource_import` of the folder's imports manager.
- **Extension:** `vscode-client/extension/documentationViewer.ts` (suggestion messages) and `vscode-client/extension/languageclientsmanger.ts` (the request to a running client).
- **Viewer page:** `vscode-client/documentationViewer/app.tsx`, `protocol.ts` and `viewer.css`.
- **Docs:** `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`.
- **Tests:** tests of the new request in `tests/robotcode/language_server/robotframework/parts/`; the list itself in the isolated VS Code harness.
- **Not in this change:**
  - A history of targets, and bookmarks. Bookmarks are planned as a separate change and take their place in the list before the completions.
  - Better completion results: like the editor, the completion lists every module on the Python path, also modules that are no libraries. The parked change `library-index` addresses that.
  - `Variables` files, which the viewer does not document.
- **Overlap:** the planned change `documentation-viewer-accessibility` gives the target field its name for screen readers. Both changes touch the same field, and the one applied second adapts to the first.
- **PyCharm:** not affected; it has no Documentation Viewer.
