# Tasks

## 1. New command names (D2)

- [x] 1.1 Rename the commands in `package.json`: `robotcode.openDocumentationViewer` becomes `robotcode.newDocumentationViewer` with the title "New Documentation Viewer", `robotcode.openDocumentationViewerInNewWindow` becomes `robotcode.copyDocumentationViewerToNewWindow` with the title "Copy Documentation Viewer into New Window", also in the menu `editor/title/context`. Register them under the new IDs in `vscode-client/extension/documentationViewer.ts`. Verify with `npm run lint`, `npm run compile`, and that `git grep openDocumentationViewer` finds the old IDs only under `openspec/changes/archive/`.
- [x] 1.2 In the `markdownDescription` of `robotcode.documentationViewer.openLocation`, name "New Documentation Viewer" (in the command palette and in a viewer's toolbar) instead of "RobotCode: Open Documentation Viewer", and regenerate the settings reference with `hatch run create-vscode-settings-docs`. Verify that `docs/src/content/docs/reference/vscode-settings.md` shows the new name.
- [x] 1.3 Use the new names in the guide: the first and last item of "Opening a viewer" in `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`, and the two rows of the command table in `docs/src/content/docs/guides/vscode/index.mdx`. In "Arranging viewers", name VS Code's *Split Editor* and *Copy Editor into New Window*, which cannot split or copy a viewer, and point to the renamed command. Verify with `npm run docs:build`.

## 2. The button New Documentation Viewer (D1, D3, D5)

- [x] 2.1 Add the button to the toolbar in `vscode-client/documentationViewer/app.tsx`, after the pin button, with the codicon `add`, label and tooltip "New Documentation Viewer"; it posts the new message `newViewer` from `protocol.ts`. In `documentationViewer.ts`, `onMessage` waits until VS Code reports the viewer as active, at most one second (D5), and then opens a new viewer on `BuiltIn` with the target field focused, in the folder of the viewer's current entry or else the viewer's folder; `openViewer()` takes that folder as an optional parameter and asks with `pickFolder()` only without it. Verify with `npm run lint` and `npm run compile`.
- [x] 2.2 Describe the button in the first item of "Opening a viewer" in `documentation-viewer.mdx`: the button in the toolbar opens a new viewer like the command, in the viewer's workspace folder. Verify with `npm run docs:build`.
- [x] 2.3 Check the scenarios of the requirement "The button New Documentation Viewer" in the VS Code harness:
  - a viewer on `Collections` at `Remove From List`: the button opens a viewer beside it on `BuiltIn` with the target field focused and its text selected, and the first viewer still shows `Collections` at `Remove From List`;
  - a workspace with two folders and a viewer of the second folder: the new viewer shows `BuiltIn` of that folder, without a folder pick;
  - with `robotcode.documentationViewer.openLocation` set to `active`, the new viewer opens in the group of the viewer;
  - with a pinned viewer, the new viewer is not pinned and "Show in Documentation Viewer" still uses the pinned one.

  Also run both renamed commands from the command palette: "New Documentation Viewer" and "Copy Documentation Viewer into New Window" work as before, and the tab's context menu shows the new name.

## 3. Screenshot (D4)

- [x] 3.1 In `playground/robotcode-demo/vscode/guide-documentation-viewer.js`, call `robotcode.newDocumentationViewer` instead of the old ID. Take the screenshots with `ctx.GUIDE_OUT` set to a scratch directory, and copy only `viewer-window-light.png` and `viewer-window-dark.png` to `docs/src/assets/screenshots/vscode/`. Verify that both show the button after the pin button and otherwise the same scene as before, and that `docs/src/assets/screenshots/vscode/viewer-side-by-side-*.png` is unchanged.

## Workflow follow-up

- Archive the change after review, with the delta spec synced into `openspec/specs/vscode-documentation-viewer/spec.md`.
