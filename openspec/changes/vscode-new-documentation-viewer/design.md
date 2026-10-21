# Design

## Context

`DocumentationViewerManager` in `vscode-client/extension/documentationViewer.ts` registers both commands. `openViewer()` picks the folder with `pickFolder()`, which takes the folder of `window.activeTextEditor`, the only folder, or asks. A viewer is a webview, not a text editor, so while a viewer is active a multi-root workspace asks for the folder. `openViewerInNewWindow()` instead takes the folder of the active or last-used viewer.

The toolbar is rendered by `vscode-client/documentationViewer/app.tsx`. Its buttons talk to the extension through the messages in `protocol.ts`, as the folder button does with `pickFolder` and the Markdown button with `openMarkdown`.

## Goals / Non-Goals

**Goals:**
- The command and the button open a new viewer through the same code. The button passes the viewer's folder; the command picks the folder as it does now.

**Non-Goals:**
- No default keybinding for the new command.
- No change to "Show in New Documentation Viewer" or to how "Copy Documentation Viewer into New Window" chooses what it copies.
- The command from the palette still asks for a folder while a viewer is active in a multi-root workspace.

## Decisions

### D1: The button sends a message, the extension opens the viewer

The button posts a new message `newViewer` to the extension. `onMessage` opens the viewer as the command does, with the folder of the viewer's current entry or else the viewer's folder, the way `openViewerInNewWindow()` finds the folder of its source. `openViewer()` takes this folder as an optional parameter and calls `pickFolder()` only without it.

*Alternative:* the page runs the command itself. A webview cannot run commands without the extension, and the command would ask for the folder in a multi-root workspace, because the active editor is the viewer and not a text editor.

### D2: New IDs, no aliases

The IDs change with the titles: `robotcode.newDocumentationViewer` and `robotcode.copyDocumentationViewerToNewWindow`. Neither command was in a release (v2.7.0 has none of the viewer's commands), so no old ID is kept as an alias.

### D3: Icon and position

The button has the codicon `add`, the plus of VS Code's "New Terminal" button, and comes last, after the pin button. The folder button stays before the pin button, as the requirement "Switching the workspace folder of a viewer" says. Its label and tooltip are "New Documentation Viewer", as for the other buttons of the toolbar.

### D4: Which media change

The static screenshot `viewer-window` (light and dark) shows the toolbar as the reference picture of the guide page, so it is taken again with `playground/robotcode-demo/vscode/guide-documentation-viewer.js`. That script calls `robotcode.openDocumentationViewer`; it gets the new ID. It also takes `viewer-side-by-side`, which is not in the repository yet and belongs to other work in progress. To leave that file alone, the script runs with `ctx.GUIDE_OUT` pointing at a scratch directory, and only `viewer-window-light.png` and `viewer-window-dark.png` are copied into `docs/src/assets/screenshots/vscode/`.

The recordings stay: `viewer-browsing` on the guide page and `vscode-documentation-viewer.mp4` of the home page's tour. They show the viewer at work; the missing button does not make what they show wrong. `viewer-source-action` shows no toolbar.

## Risks / Trade-offs

- [The planned change `documentation-viewer-accessibility` also edits the toolbar in `app.tsx`, which it names as one group.] → The button is one more control in that group. Whichever change lands second adds it there; no requirement of either change conflicts.
- [Someone runs the old command ID from a script or a keybinding made with a development build.] → Not released, so only development builds are affected; VS Code reports the unknown command.
