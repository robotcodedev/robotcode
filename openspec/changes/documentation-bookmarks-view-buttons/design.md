# Design

## Context

- **Choosing a viewer.** `DocumentationViewerManager` (`vscode-client/extension/documentationViewer.ts`) shows documentation from the editor in `viewerToShow`: the pinned viewer (`_pinned`), else the viewer used last (`lastUsedViewer()`), brought forward with `panel.reveal(panel.viewColumn, true)`, so the editor keeps the focus; without one it creates a viewer beside the active editor. A viewer counts as used when it is active (`onDidChangeViewState`, after `ACTIVATION_DELAY_MS`) or when an action shows something in it (`markUsed`).
- **New Documentation Viewer.** `openViewer(folder?)` creates a viewer on `BuiltIn` where `robotcode.documentationViewer.openLocation` says (`openColumn()`), with the focus in its target field. Without a folder it calls `pickFolder()`: the folder of the active text editor, else the only folder, else a pick.
- **Focus of a viewer.** Panels have no `retainContextWhenHidden`: a hidden viewer loads its page again when it is shown, and restores its target, place and history from its state. On `ready`, the extension posts `focus` when the panel is active or `focusOnReady` is set, and the page focuses its content unless something in it has the focus.
- **The view.** `robotcode.documentationBookmarksView` in the Explorer, visible while a Robot Framework file or a viewer is the active editor. Its title has one action, Reset Documentation Bookmarks (`view/title`, group `navigation`).
- **Icons.** The tab of a viewer has the icon `book` (`panel.iconPath`). The command `robotcode.newDocumentationViewer` declares `$(book)`, but no menu shows it; the same action in a viewer's toolbar has the icon `add`.

## Goals / Non-Goals

**Goals:**
- One command that brings the viewer the actions use to the front with the focus, from the palette and from the view.
- The view's buttons look like the viewer's own: the book of its tabs for the viewer, `add` for a new one.

**Non-Goals:**
- A change to how the actions of the editor choose or show a viewer.
- A change to the folder that New Documentation Viewer takes.

## Decisions

### D1: Show Documentation Viewer

- **The command** `robotcode.showDocumentationViewer`, title "Show Documentation Viewer", category RobotCode, icon `$(book)`, registered in `DocumentationViewerManager`.
- **With a viewer.** The command takes `_pinned ?? lastUsedViewer()`, calls `panel.reveal(panel.viewColumn, false)` and `markUsed`. The viewer stays in its editor group and window, and VS Code brings that window to the front. A hidden viewer loads its page again, and the `ready` message gives it the focus because its panel is active.
- **Without a viewer.** The command calls `openViewer()`, so it behaves exactly as New Documentation Viewer from the palette.

**Alternatives considered:**
- **`viewerToShow(false, …)`.** It keeps the focus where it is, and without a viewer it opens one beside the active editor without the focus. The user decided that the viewer gets the focus, as a click on its tab gives it.
- **Revealing in `openColumn()`.** That would move the viewer into another group; the viewer is shown where the user put it.

### D2: The buttons of the view

- **Menu.** `view/title` with `when: view == robotcode.documentationBookmarksView`: Show Documentation Viewer at `navigation@1`, New Documentation Viewer at `navigation@2`, Reset Documentation Bookmarks at `navigation@3`, which today has `navigation` without an order.
- **Icons.** Show Documentation Viewer gets `$(book)`, the icon of the viewer's tabs. The command New Documentation Viewer changes its icon from `$(book)` to `$(add)`, the icon of its button in a viewer's toolbar; the old icon is shown nowhere.

**Alternatives considered:**
- **New Documentation Viewer and Copy Documentation Viewer into New Window as the buttons.** The user chose Show Documentation Viewer and New Documentation Viewer.

### D3: Docs

`docs/src/content/docs/guides/vscode/documentation-viewer.mdx`: *RobotCode: Show Documentation Viewer* in "Opening a viewer", and the two buttons in the paragraph of the view Documentation Bookmarks, next to Reset.

### D4: Tests

The isolated VS Code harness checks the scenarios: the order of the buttons, Show Documentation Viewer with the viewer used last, with a pinned viewer, without a viewer and with a viewer in another window, Show from the view with a viewer hidden behind a `.robot` file, and New Documentation Viewer from the view. The command palette has the command. There is no unit test: the command only reveals a panel.

## Risks / Trade-offs

- [VS Code shows the actions of a view in the Explorer only while the mouse is over its header or the view has the focus.] → As for Reset today; the command palette has Show Documentation Viewer too.
- [Xvfb has no window manager, so the harness may not see a window come to the front.] → The harness checks which window is focused (`BrowserWindow.getFocusedWindow()`) and that the viewer's panel is active in it; if Xvfb cannot show it, the report says so.
- [With several workspace folders, New Documentation Viewer asks for the folder while a viewer is the active editor, since `pickFolder()` only looks at the active text editor.] → The same as from the command palette; not changed here.

## Migration Plan

Nothing to migrate.
