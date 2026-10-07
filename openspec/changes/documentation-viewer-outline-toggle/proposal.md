# Proposal: documentation-viewer-outline-toggle

## Why

The outline of a Documentation Viewer always takes part of the viewer's width. It can be dragged narrower, but not hidden, so a page in a narrow editor group cannot get the full width of its viewer.

## What Changes

- **Outline button.** The toolbar gets a button at its start that hides and shows the outline together with its filter field. While the outline is hidden, the page takes the full width of the viewer.
- **Per viewer.** Each viewer keeps whether its outline is shown, as it keeps its filter and the width of the outline, also after a reload of the window.
- **Setting for new viewers.** The setting `robotcode.documentationViewer.showOutline`, `true` by default, decides whether a new viewer starts with its outline. Changing it leaves open viewers as they are.
- **Nothing else moves.** Hiding and showing the outline keeps the page at its position, and keeps the filter text and the collapsed entries of the outline.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-documentation-viewer`: the outline of a viewer can be hidden and shown again, a viewer keeps whether it is shown, and a setting decides how a new viewer starts.

## Impact

- **Code:**
  - `package.json`: the setting `robotcode.documentationViewer.showOutline`.
  - `vscode-client/extension/documentationViewer.ts`: hands the setting to a viewer.
  - `vscode-client/documentationViewer/protocol.ts`: the viewer state records a hidden outline.
  - `vscode-client/documentationViewer/app.tsx` and `viewer.css`: the button and the layout without the outline.
- **Docs:** `docs/src/content/docs/guides/browsing-documentation.md`, section "Outline and filter".
- **Tests:** The VS Code viewer has no JavaScript tests and is checked in the isolated VS Code harness.
- **Users:** One new setting; its default keeps today's behavior. A saved viewer state of an older version starts as the setting says.
