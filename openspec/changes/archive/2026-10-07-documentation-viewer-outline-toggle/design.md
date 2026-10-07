# Design: documentation-viewer-outline-toggle

## Context

See proposal.md for the problem. The facts below were checked on 2026-10-07.

- **Layout.** The body of a viewer is a `vscode-split-layout`: the filter field and the outline in its start pane, the page in its end pane. The width of the start pane is saved in the viewer state as `split`. A resize handler sets the saved width again when the viewer gets wider, because the split layout narrows the outline in a narrow viewer.
- **Split layout.** `vscode-split-layout` of `@vscode-elements/elements` 2.5.1 cannot collapse a pane. It has `handlePosition`, `minStart`, `minEnd`, `fixedPane` and `handleSize`.
- **Page.** The page is rendered into the `main` element, which the controller gets once at the start. A new `main` element would need the page rendered again and its position restored.
- **State.** `ViewerState` (version 1) has optional fields, such as `split`. The pin button is a toggleable `vscode-toolbar-button` whose label says what a click does.
- **Outline.** The outline scrolls the selected entry into view when the selection or the page changes.
- **Extension.** The extension sets the HTML of a viewer's webview when it creates the viewer and when VS Code restores it after a reload. It reads the settings of the viewer under `robotcode.documentationViewer`, such as `openLocation`, without a workspace folder.

## Goals / Non-Goals

**Goals:**
- Hide and show the outline per viewer, with the state kept as the other viewer state is.
- A setting for whether a new viewer starts with its outline.

**Non-Goals:**
- No VS Code command and no key for the button.
- No change to open viewers when the setting changes; it decides only how a viewer starts.
- No automatic hiding in a narrow viewer; the split layout narrows the outline there already.
- No change to the terminal viewer, whose sidebar is hidden until `s` is pressed.

## Decisions

### D1: A toggle button at the start of the toolbar

- A toggleable `vscode-toolbar-button` before Back and Forward, above the outline it controls, checked while the outline is shown.
- Its codicon is `layout-sidebar-left` while the outline is shown and `layout-sidebar-left-off` while it is hidden, as VS Code's own side bar toggles switch them.
- Its label and tooltip say what a click does: `Hide Outline` or `Show Outline`, as the pin button does.

Alternatives considered:
- **A command with a key.** The maintainer chose the button only.
- **A fixed label `Toggle Outline`.** It does not say whether the outline is hidden.

### D2: An optional field in the viewer state

`ViewerState` gets `outlineHidden?: boolean`. A new viewer and the state of an older version have no such field; they start as the setting says (D5) and keep that value in their state from then on. The version stays 1, because the field is optional.

### D3: The split layout stays while the outline is hidden

While the outline is hidden, the start pane is collapsed to zero width, without a handle to drag, and its content is not shown. The page stays in its `main` element and keeps its position. Showing the outline sets the saved width again. The resize handler leaves a hidden outline hidden.

Alternative considered:
- **The page without the split layout while the outline is hidden.** Preact creates the `main` element anew under another parent, so the page would have to be rendered again and its position restored.

### D4: The selected entry is visible when the outline is shown again

The page can move while the outline is hidden, by links, actions, back and forward. When the outline is shown again, it scrolls the selected entry into view, as it does when the selection changes.

### D5: The setting reaches the viewer with its HTML

- `robotcode.documentationViewer.showOutline` is a boolean setting, `true` by default, read without a workspace folder as `openLocation` is.
- The extension writes its value into the HTML of the webview, as a data attribute of the root element, when it sets the HTML. The viewer reads it before its first render, so a viewer that starts without its outline does not show it first.
- The viewer uses the value only while its state has no `outlineHidden`. A change of the setting therefore reaches new viewers, and open viewers keep their own state.

Alternative considered:
- **A message after the viewer is ready.** The viewer renders before the message arrives, so its outline would appear and vanish again.

## Risks / Trade-offs

- [The split layout may keep a visible or draggable separator at zero width] → `handleSize` and the separator colour are set while the outline is hidden; if that is not enough, the end pane is laid out without the split layout and the page is rendered again at its position, as in the alternative of D3.
- [The VS Code viewer has no JavaScript tests] → The scenarios are checked in the isolated VS Code harness.

## Migration Plan

Nothing for users to do. A saved state without the new field starts as the setting says, which shows the outline by default. Rollback is a revert; a saved `outlineHidden` and the setting are then ignored.
