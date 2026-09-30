# Proposal: doc-viewer-sidebar

## Why

`robotcode doc browse` and the REPL's `.doc` show the page of a library in RobotCode's documentation viewer as one long document. To reach a keyword, the user scrolls to the keyword index at the start of `Keywords` and cycles through its links, or searches the whole text with `/`, which also hits every mention in the documentation. Libdoc's HTML output has a sidebar with the sections and keywords of the library and a filter field that narrows the list while typing. The maintainer wants the same in the terminal (maintainer decision, 2026-09-30).

## What Changes

- **A sidebar with the outline of the page** in the documentation viewer: the sections of the introduction, `Importing`, every keyword and every data type, grouped under their level-2 heading, as in Libdoc's sidebar (maintainer decision).
- **Hidden until `s` is pressed** (maintainer decision). The page keeps the full width until then.
- **Filter while typing** (maintainer decision): a filter field above the list narrows the entries, with the rules of the patterns of `robotcode doc keywords` (contains, `*` and `?`, case, spaces and underscores ignored). `Enter` or a click jumps to the selected heading; `[` goes back.
- **Side by side or on top, depending on the width** (maintainer decision): in a wide terminal the sidebar stands left of the page, which is rendered narrower, and stays open after a jump. In a narrow terminal it lies over the left part of the page and closes after a jump, so the page keeps its width.
- **Only for the page of a library, resource file or suite file** (maintainer decision): `robotcode doc browse` and `.doc` in the REPL and at a `robot-debug` stop. `.help`, `.kw`, `.source` and the other views of the viewer have no sidebar.
- **Docs:** the viewer's key table in `docs/03_reference/repl.md` and the `browse` section of `docs/03_reference/browsing-documentation.md`.
- **Not in this change:** a sidebar in other views of the viewer, a sidebar in the plain backend of the REPL (which prints documentation without the viewer), and changes to the page itself.

Builds on `doc-cli`: the page structure (`Keywords` and `Data types` with level-3 headings), `heading_anchors` and the viewer's anchor map built from it. It is applied after `doc-cli`.

## Capabilities

### New Capabilities

- `documentation-viewer-sidebar`: The sidebar of the documentation viewer for the page of a library, resource file or suite file: what it lists, when it is available and shown, the filter, jumping to a heading, and the layout in wide and narrow terminals.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/repl/src/robotcode/repl/_pt/doc_viewer.py`: the sidebar (outline, filter field, list), its layout next to or over the body, the key bindings, the width of the body, and the reflow when the sidebar is shown or hidden side by side.
- `packages/repl/src/robotcode/repl/prompt_toolkit_interpreter.py` and `console_interpreter.py`: `show_doc` passes whether the document is a library page; `.doc` passes it. `packages/repl/src/robotcode/repl/doc_cli.py`: `browse` passes it.
- Tests in `tests/robotcode/repl/test_doc_viewer.py` and `test_doc_cli.py`, on RF 5.0–7.5 (Linux, Windows, macOS).
- Docs: `docs/03_reference/repl.md`, `docs/03_reference/browsing-documentation.md`.
- No new dependency; prompt_toolkit and Robot Framework's `MultiMatcher` are already used by the REPL package. Unchanged: the page, the plain backend, the language server, the editor extensions.
