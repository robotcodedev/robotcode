# Design

## Context

- **The outline** is the page's own tree (`vscode-client/documentationViewer/outline.tsx`). Its rows are plain elements with the entry's id (`data-id`), title and kind (`keyword`, `type`, `heading`, or a section row). A click calls `Controller.choose`, which shows the heading as a new history entry (`showAnchor`). An outline built without rendered HTML is static: choosing an entry only selects it.
- **VS Code's webview menus** (VS Code 1.143.1, `webviewElement.ts`, `pre/index.html`):
  - The webview listens for `contextmenu` in the page. It merges the JSON of `data-vscode-context` of the target and its ancestors (`closest`), and shows the menu `webview/context` with those values as context keys and `webviewId`.
  - The command of an entry gets the merged values and `webview`, the view type, but not the panel.
  - The value `preventDefaultContextMenuItems` hides Cut, Copy and Paste.
- **The page message** carries the keywords and types as `{name, anchor}`; the extension keeps the Markdown of the page shown last (`Viewer.lastPage`) for Open as Markdown.
- **Bookmarks** are kept by the store of `documentation-viewer-bookmarks` (`documentationViewerBookmarks.ts`): `add(folder, bookmark)` puts a place into the folder's group, and `removePlace(folder, bookmark)` removes it from the folder and from All Workspaces.
- **`robotcode doc`** writes keyword entries from `KeywordDoc` (`packages/repl/src/robotcode/repl/doc_cli.py`, `KeywordEntry`). `KeywordDoc` has `source`, an absolute path, and `line_no`, 1-based: for example `Collections.py` of the environment at 389 for `Get Slice From List`, and `libraries/ShopLibrary.py` at 83 for `Order Status`.

## Goals / Non-Goals

**Goals:**
- One menu for all rows, whose entries depend on the row's kind and state, with VS Code's own context menus and their keyboard access.
- Go to Source that opens only files the extension knows from the page it generated.

**Non-Goals:**
- A menu on the page itself or in the filter field.
- A source for data types, which Libdoc does not give.

## Decisions

### D1: The menu of a row

- **Context of a row.** A row of an outline that is not static gets a `data-vscode-context`:
  - `webviewSection` `outlineEntry` and `preventDefaultContextMenuItems`;
  - `viewerId`, the viewer's id from its state (`ViewerState.id`), since the command learns the view type but not the panel;
  - `anchor` and `title` of the entry;
  - `entryBookmarked`, whether a bookmark that holds for the viewer's folder has the entry's target and anchor;
  - `entryHasSource`, whether the entry is a keyword whose source the page message names.
- **Entries.** The menu `webview/context` gets five commands, each with `webviewId == 'robotcode.documentationViewer' && webviewSection == 'outlineEntry'`, hidden in the palette:
  - `robotcode.documentationViewer.openEntry` (Open) and `robotcode.documentationViewer.openEntryInNewViewer` (Open in New Documentation Viewer), group `1_open`;
  - `robotcode.documentationViewer.goToEntrySource` (Go to Source), group `2_source`, also with `entryHasSource`;
  - `robotcode.documentationViewer.addEntryBookmark` (Add Bookmark), with `!entryBookmarked`, and `robotcode.documentationViewer.removeEntryBookmark` (Remove Bookmark), with `entryBookmarked`, group `3_bookmark`.
- **Elsewhere.** The filter field, the page and the rows of a static outline get no context, so VS Code's Cut, Copy and Paste stay there.
- **Keyboard.** The context menu key and Shift+F10 fire `contextmenu` on the focused row, which VS Code's listener takes as a right-click. The harness checks it.

**Alternatives considered:**
- **A menu of the page's own**, drawn in the webview. VS Code's menu looks and behaves like VS Code's other menus, also for screen readers and the keyboard, and needs no code for either.

### D2: What the commands do

The extension finds the viewer by `viewerId` among its viewers, and takes the target and folder from the viewer's current entry.

- **Open** posts `{type: "openEntry", anchor}` to the viewer. The page chooses the entry as a click does (`choose`).
- **Open in New Documentation Viewer** shows the target at `anchor` in a new viewer, as *Show in New Documentation Viewer* does (`viewerToShow(true, …)`).
- **Add Bookmark** adds `{text, heading: anchor, title}` to the group of the viewer's folder. **Remove Bookmark** removes that place from the folder and from All Workspaces, as the star does.
- **Go to Source** looks the keyword up by `anchor` in the keywords of the page the extension sent last, which it keeps with their source and line. It opens the file at `lineno - 1`:
  - in the group of the text editor used last, which the manager remembers from `onDidChangeActiveTextEditor`, while that group still exists;
  - else beside the viewer (`ViewColumn.Beside` of the active group, the viewer's).

### D3: The trust boundary

- **Paths from the extension only.** The file of Go to Source comes from the extension's copy of the page, never from the menu's context, which the page sets.
- **No context from documentation.** `renderPage` removes the attribute `data-vscode-context` from documentation, as it removes `style` and the event handlers (`isBlocked`), so that documentation cannot add the outline's entries to its own elements or remove Cut, Copy and Paste.

### D4: The source in `robotcode doc`

- **Fields.** `KeywordEntry` gets `source`, `kw.source` or empty, and `lineno`, `kw.line_no`, or `-1` when it is unknown, as the JSON has them for the library. The JSON of `keywords` and `keyword` gets them too, since it has the same entries.
- **Into the page.** The extension passes `source` and `lineno` of each keyword whose file and line are both known into the page message, from which the page sets `entryHasSource`, and keeps them with the page for Go to Source. A dynamic library can name the file of a keyword without its line (`lineno` `-1`); such a keyword has no Go to Source.

### D5: Tests

- **`robotcode doc`.** `tests/robotcode/repl/test_doc_cli.py`: the field set of a keyword entry, `Collections.py` and the method's line for a library keyword, and the file and line of a keyword of a resource file.
- **The rest.** The isolated VS Code harness checks the scenarios of the specs: the entries of each kind of row, Open, the new viewer, the bookmarks, Go to Source with and without a text editor used before, the keyboard, the filter field and the page, and documentation with `data-vscode-context`.

## Risks / Trade-offs

- [The context menu key or Shift+F10 does not open VS Code's webview menu in a version VS Code supports.] → The harness checks VS Code 1.127, the minimum, and the current version. If a version does not, the guide says so.
- [A kept page was generated before the file changed.] → Go to Source opens the file at the line of that page; the generation in the background updates the page.
- [Go to Source opens a library's file in the Python environment, where an edit changes the installed library.] → The same as Go to Definition in the editor.

## Migration Plan

Nothing to migrate. The JSON of `robotcode doc` gets two fields; readers of the JSON that ignore unknown fields keep working.
