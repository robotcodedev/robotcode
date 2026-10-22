# Proposal

## Why

"RobotCode: Open Documentation Viewer" opens a new viewer on every call, but "Open" reads as if there were one viewer that the command brings forward. Inside a viewer there is no way to open a second one: its toolbar has no button for it, and the tab's context menu only copies the viewer into a new window. The two commands are new in the coming release, so their names and IDs can still change.

## What Changes

- The command `robotcode.openDocumentationViewer` becomes `robotcode.newDocumentationViewer`, titled "RobotCode: New Documentation Viewer". It behaves as before: a new viewer on `BuiltIn`, with the target field focused and its text selected.
- The command `robotcode.openDocumentationViewerInNewWindow` becomes `robotcode.copyDocumentationViewerToNewWindow`, titled "RobotCode: Copy Documentation Viewer into New Window", in the command palette and in the context menu of a viewer's tab. It behaves as before.
- The toolbar of a viewer gets the button "New Documentation Viewer", after the pin button. It opens a new viewer on `BuiltIn` of the viewer's workspace folder, with the target field focused and its text selected, where `robotcode.documentationViewer.openLocation` says.
- The VS Code guide, the command table, the description of `robotcode.documentationViewer.openLocation` and the settings reference use the new names and describe the button; the screenshot of the viewer shows the new toolbar.

Neither command was in a release (v2.7.0 has none of the viewer's commands), so the renames are not breaking.

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-documentation-viewer`: the two commands get their new names, and the toolbar gets the button "New Documentation Viewer".

## Impact

- **Code:** `package.json` (commands, menu, setting description), `vscode-client/extension/documentationViewer.ts` (command registrations, the message of the new button), `vscode-client/documentationViewer/app.tsx` and `protocol.ts` (the button and its message).
- **Docs:** `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`, the command table in `docs/src/content/docs/guides/vscode/index.mdx`, the generated `docs/src/content/docs/reference/vscode-settings.md`, the screenshot `viewer-window` (light and dark).
- **Users:** the commands have new names in the command palette; each viewer has one more button.
