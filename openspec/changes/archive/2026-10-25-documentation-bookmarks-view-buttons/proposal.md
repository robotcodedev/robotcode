# Proposal

## Why

The view Documentation Bookmarks opens a viewer only through a bookmark. To get to the viewer itself, or to start a new one without a bookmark, the user needs the command palette, an action in the editor or the toolbar of a viewer. There is also no command that brings the viewer the actions use to the front, for example when its tab is hidden behind other editors or the viewer is in another window.

## What Changes

- **The command Show Documentation Viewer.** "RobotCode: Show Documentation Viewer", in the command palette and as a button in the title of the view Documentation Bookmarks:
  - It shows the viewer the actions use, the pinned viewer or else the viewer used last, and gives it the focus, as a click on its tab does.
  - The viewer keeps its target, place and history. A viewer in another window comes to the front there.
  - Without a viewer, it opens a new one on `BuiltIn`, as New Documentation Viewer does.
- **New Documentation Viewer in the view.** The command New Documentation Viewer becomes a button in the title of the view, with the icon `new-file`, which the same button in a viewer's toolbar gets as well.
- **The order of the buttons.** Show Documentation Viewer, New Documentation Viewer, then Reset Documentation Bookmarks, which is there already.

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-documentation-viewer`: the command Show Documentation Viewer, and the buttons in the title of the view Documentation Bookmarks.

## Impact

- **Extension:**
  - `package.json`: the command, the icon of New Documentation Viewer, and the menu `view/title` of the view.
  - `vscode-client/extension/documentationViewer.ts`: the command Show Documentation Viewer.
- **Viewer page:** `vscode-client/documentationViewer/app.tsx`: the icon of the button New Documentation Viewer in the toolbar.
- **Docs:** `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`.
- **Not in this change:**
  - A button for Copy Documentation Viewer into New Window. The user chose Show Documentation Viewer and New Documentation Viewer over it.
  - The folder of New Documentation Viewer. With several workspace folders, while a viewer is the active editor, the command asks for the folder, from the button as from the command palette.
