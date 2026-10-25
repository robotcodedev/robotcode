# Proposal

## Why

A right-click on an entry of the outline of a Documentation Viewer shows VS Code's Cut, Copy and Paste, which do nothing for an entry. What a user wants to do with an entry is not reachable there: open it in a new viewer, bookmark it without scrolling to it first, or look at the source of a keyword.

## What Changes

- **A context menu for the rows of the outline**, in place of Cut, Copy and Paste:
  - *Open* shows the entry in the same viewer, as a click does.
  - *Open in New Documentation Viewer* shows the target at the entry in a new viewer.
  - *Add Bookmark*, or *Remove Bookmark* while the entry's place is bookmarked, works on the place of the entry as the star does on the place at the top of the view.
  - *Go to Source*, for keywords whose file and line are known, opens the file at the keyword's line: a resource or suite file, a library of the project, or a library of the Python environment. It opens in the editor group of the text editor used last, or beside the viewer without one.
- **Rows without a source.** Data types, the headings of the introduction and the rows of the sections (Introduction, Importing, Keywords, Data types) get the same menu without *Go to Source*.
- **The rest of the viewer keeps VS Code's menu.** The filter field and the page keep Cut, Copy and Paste, which work on text there.
- **The keyboard.** The menu opens on the focused row with the context menu key or Shift+F10 as well.
- **Documentation does not change the menu.** HTML in documentation cannot set what the menu offers.
- **`robotcode doc` names the source of each keyword.** Each keyword entry of the JSON output gets `source` and `lineno`, the file of the keyword and its line, as the output has them for the library: empty and `-1` when they are unknown. The CLI guide lists the two fields.

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-documentation-viewer`: the context menu of the outline's rows, with Open, Open in New Documentation Viewer, the bookmarks and Go to Source.
- `documentation-cli`: the keyword entries of the JSON output have `source` and `lineno`.
- `vscode-user-guide`: the page Documentation Viewer explains the context menu of the outline.

## Impact

- **`robotcode doc`:** `packages/repl/src/robotcode/repl/doc_cli.py` (the keyword entries) and its tests in `tests/robotcode/repl/test_doc_cli.py`.
- **Extension:**
  - `vscode-client/extension/documentationViewer.ts`: the commands of the menu, the keywords' source in the page message, and the text editor used last.
  - `package.json`: the commands and the menu `webview/context`.
- **Viewer page:** `vscode-client/documentationViewer/outline.tsx` and `app.tsx` give each row the context of the menu; `page.ts` keeps documentation from setting it; `protocol.ts` carries the new messages and the keywords' source.
- **Docs:** `docs/src/content/docs/guides/vscode/documentation-viewer.mdx` and the JSON fields in `docs/src/content/docs/guides/browsing-documentation.md`.
- **Not in this change:** copying the name or the place of an entry, and inserting a keyword into the editor, which the user decided against; a source for data types, which Libdoc does not give.
