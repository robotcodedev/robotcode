# Tasks: doc-viewer-sidebar

## 1. Prerequisite

- [x] 1.1 Confirm that `doc-cli` is applied: `_build_anchor_to_line_map` in `packages/repl/src/robotcode/repl/_pt/doc_viewer.py` uses `heading_anchors`, and `robotcode doc browse` exists. Verify with `hatch run test:test -- tests/robotcode/repl/test_doc_viewer.py tests/robotcode/repl/test_doc_cli.py`.

## 2. The sidebar in the viewer

- [x] 2.1 Build the outline of a document (design D1): level-2 headings and their level-3 headings from `heading_anchors`, titles without Markdown markers, entries without a rendered line left out. Add `outline: bool = False` to `DocViewer.run` and keep it per loaded document, also in `_NavState` (design D2). Verify in `tests/robotcode/repl/test_doc_viewer.py`: the outline of the `Collections` page starts with `Introduction` and lists every keyword of the page below `Keywords` in page order; a heading at level 5 is not listed; a document loaded without `outline=True` has none.
- [x] 2.2 Add the sidebar to the layout (design D3): a 32-column list with a filter field, side by side through a `VSplit` from 94 columns, otherwise as a `Float` over the body; one helper for the body width, used by `_load_document`, `_check_resize` and the toggle. Verify in `test_doc_viewer.py` with the output size patched: at 120 columns the sidebar is side by side and the body is rendered at 86 columns; at 80 columns it is on top and the body keeps 78 columns; a resize to 80 columns while the page has the focus hides it (design D3).
- [x] 2.3 Add the keys and the focus rules (design D4): `s` on a page with an outline, filter input, up/down, `Enter`, `Esc`, mouse click, the selection of the heading at the top when the sidebar gets the focus, and the footer texts. Verify in `test_doc_viewer.py` through the key handlers: `s` on a `.kw`-like document without the flag does nothing; `Enter` on `Get Match Count` scrolls to its heading and `_go_back()` returns; side by side the sidebar stays visible and the body has the focus, on top it is hidden; `Esc` hides it without changing the scroll.
- [x] 2.4 Add the filter (design D5). Verify in `test_doc_viewer.py` on the `Collections` page, on every RF version: `dict` lists only entries containing `dict` and keeps `Keywords`; `get*list` and `get_from_list` list `Get From List`; an empty filter lists everything; the selection moves to the first entry that matches itself, not to a level-2 entry listed only for its entries (design D5).
- [x] 2.5 Reflow when the sidebar is shown or hidden side by side (design D6): keep the heading at the top, run the search again, drop the history and the focused link. Verify in `test_doc_viewer.py` at 120 columns: with `Get Match Count` at the top, showing and hiding the sidebar keeps it at the top each time; a search for `dictionary` still has matches after the toggle; on top nothing is reflowed.
- [x] 2.6 Let `Esc` on the page hide a sidebar that stands beside the page before it closes the viewer, and name it in the footer hints (design D4, maintainer decision 2026-10-01). Verify in `test_doc_viewer.py` at 120 columns: after a jump from the sidebar, `Esc` hides the sidebar, keeps the heading at the top and leaves the viewer open; a second `Esc` closes it.
- [x] 2.7 Let the mouse wheel over the sidebar's list scroll the list without changing the selection, and scroll a selection moved by up, down, the filter or `s` into view (design D4, maintainer decision 2026-10-01). Verify in `test_doc_viewer.py` that the entries leave the wheel to the list's window, whose cursor follows its scroll and not the selection, and that up and down after a scroll bring the selection back into view.

## 3. Callers

- [x] 3.1 Pass `outline=True` from `robotcode doc browse` (`doc_cli.py`) and, through `show_doc(..., outline=...)` of both backends, from `.doc` (`console_interpreter.py`, `prompt_toolkit_interpreter.py`); the plain backend ignores it. Verify in `tests/robotcode/repl/test_doc_cli.py` that `browse` starts the viewer with `outline=True`, and in `tests/robotcode/repl/test_dot_commands.py` that `.doc` passes it while `.kw` and `.help` do not.

## 4. Documentation

- [x] 4.1 Add `s` and the sidebar's keys to the viewer's key table in `docs/03_reference/repl.md` (for `.doc`), and describe the sidebar in the `browse` section of `docs/03_reference/browsing-documentation.md`, with the two layouts. Verify with `npm run docs:build` and `npm run docs-next:build`.

## 5. Verification

- [ ] 5.1 Run `hatch run lint:all` and `hatch run test:test` (RF 5.0–7.5) and confirm that both pass. Confirm that the CI matrix on Linux, Windows and macOS is green.
- [ ] 5.2 Run `robotcode doc browse BuiltIn` in a terminal with at least 120 columns and in one with 80 columns: open the sidebar with `s`, filter for `should be`, jump to a keyword, go back with `[`, hide the sidebar with `Esc`, and in the wide terminal check that the heading at the top stays in place when the sidebar is shown and hidden.
