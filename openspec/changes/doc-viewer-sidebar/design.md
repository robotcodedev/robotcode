# Design: doc-viewer-sidebar

## Context

See proposal.md for the motivation and specs/ for the behaviour. The current state of the viewer (`packages/repl/src/robotcode/repl/_pt/doc_viewer.py`, with the changes of `doc-cli`):

- **Layout.** `DocViewer` builds one full-screen prompt_toolkit `Application` once: a `Frame` around an `HSplit` of the body `Window`, the search row and the footer, the two last ones behind `ConditionalContainer`s. `mouse_support=True` makes links clickable. `run(title, markdown, *, scroll_to=None)` loads a document and runs the application; `_load_document` also serves in-place link follows through the `link_resolver`.
- **Width and reflow.** The body is rendered by `rich` at a fixed width, `max(columns - 2, 40)`, computed in `_load_document` and in `_check_resize`. Renders are cached per width (`_render_cache`). A width change reflows after a debounce (`_reflow_after_resize`): the scroll position is kept as a percentage, and the back/forward history, the search matches and the focused link are dropped, because they hold positions in the old rendering. According to the code's comments, rendering `BuiltIn` takes about 300–400 ms.
- **Anchors.** `_anchor_to_line` maps each heading's anchor to its rendered line. Since `doc-cli` it is built from `heading_anchors`, the same numbered anchors the page's links use. An `#anchor` jump pushes the current position onto the back stack (`_NavState`: title, markdown, scroll, focused link).
- **Keys in use:** `Esc`, `q`, `Enter`, `j`/`k`/arrows, `PgUp`/`PgDn`, `Ctrl-D`/`Ctrl-U`, space, `b`, `g`/`G`/`Home`/`End`, `/`, `n`/`N`, `Tab`/`Shift-Tab`, `f`, `[`, `]`. `s` is free.
- **Callers.** `robotcode doc browse` calls `DocViewer().run(name, page)` (`doc_cli.py`). The REPL's prompt_toolkit backend calls `self._doc_viewer.run(...)` from `show_doc` (`prompt_toolkit_interpreter.py:130-140`), which `.doc`, `.kw`, `.help` and `.source` use (`console_interpreter.py`). The plain backend's `show_doc` prints the Markdown without the viewer.
- **Page.** Since `doc-cli`, the page has level-2 sections (`Introduction`, `Importing`, `Keywords`, `Data types`) with level-3 headings below them (sections of the introduction, keywords, data types). Keyword documentation starts at level 5.

## Goals / Non-Goals

**Goals:**
- A sidebar that makes every keyword of a library page reachable in a few keys, in wide and narrow terminals.
- No change for the other views of the viewer and for pages while the sidebar is hidden.

**Non-Goals:**
- A sidebar for `.help`, `.kw`, `.source` or documents loaded through a link (maintainer decision).
- Keeping the back/forward history across a reflow; the existing resize rule applies.
- Changing the page or the plain backend.

## Decisions

### D1: The outline comes from the page's headings

The entries are the level-2 headings of the Markdown and, below each, its level-3 headings, taken from `heading_anchors` in document order: the same walk that builds `_anchor_to_line`, so every entry jumps through the anchor map. Titles are shown as the page shows them, with the Markdown markers removed (`_strip_md_emphasis`); level-3 entries are indented by two spaces. An entry whose anchor has no rendered line is left out. The outline is built once per loaded document; it does not depend on the width.

Rejected: passing the keyword list from `LibraryDoc` to the viewer. The viewer gets Markdown from both callers and already knows its headings; a second data path would have to stay in sync with the page.

### D2: Only library pages get a sidebar

`DocViewer.run` gets a keyword argument `outline: bool = False`. `robotcode doc browse` passes `True`. The REPL passes it through `show_doc(..., outline=...)` of both backends (the plain backend ignores it), and only `.doc` sets it (maintainer decision). The flag belongs to the loaded document: `_NavState` records it, and a document loaded in place through the `link_resolver` has no sidebar. Without the flag, `s` is not bound (its filter is false), and the footer does not mention it.

### D3: Side by side when the page keeps 60 columns, otherwise on top

Maintainer decision: both layouts, chosen by the width.

- The sidebar is 32 columns wide, including a one-column border to the page. Longer entries end with `…`.
- **Side by side** when `columns - 2 - 32 >= 60`, that is from 94 columns: the frame's body becomes a `VSplit` of the sidebar and the body window, and the body is rendered at `columns - 2 - 32`.
- **On top** otherwise: the sidebar is a `Float` at the left edge of the body, over the page, which keeps `max(columns - 2, 40)`.
- The mode is computed from the terminal width whenever the layout is drawn. A resize while the sidebar is shown switches the mode and reflows as any resize does. A resize that leaves no room beside the page while the page has the focus hides the sidebar, because on top it would cover the page the user reads (found during implementation).

A single helper computes the body width from the terminal width, the sidebar's visibility and the mode. `_load_document`, `_check_resize` and the toggle use it, instead of the two inline `max(columns - 2, 40)` today.

Rejected: only side by side, because below about 94 columns too little text would remain. Only on top would cover part of the page for as long as the sidebar is open.

### D4: Keys and focus

- On the page, `s` shows the sidebar if it is hidden and gives the focus to its filter field. If the sidebar is already shown side by side, `s` just moves the focus there.
- In the sidebar, text goes into the filter field, so `q`, `j` or `s` are filter text there. The other keys:
  - **Up/Down:** move the selection.
  - **`Enter`:** jumps to the selected entry.
  - **`Esc`:** hides the sidebar and returns the focus to the page.
- When the sidebar gets the focus, the entry of the heading at the top of the page is selected, so that up and down move from where the reader is.
- **Jumping:**
  - A jump uses the anchor jump of `_follow_current_link`: the current position goes onto the back stack and the forward stack is cleared, so `[` returns.
  - Side by side, the focus then moves to the page and the sidebar stays.
  - On top, the sidebar closes.
- A mouse click on an entry jumps like `Enter`. The mouse wheel over the list scrolls the list and leaves the selection alone (maintainer decision, 2026-10-01). Like the body, the list pins prompt_toolkit's cursor to its top visible line, so prompt_toolkit's own wheel scrolling is not undone; when up, down, the filter or `s` move the selection, the sidebar scrolls the list just enough to show it.
- On the page, `Esc` closes what lies on top first (maintainer decision, 2026-10-01): while the sidebar stands beside the page, `Esc` hides it, and only the next `Esc` closes the viewer. Before, `Esc` on the page always closed the viewer, so `Esc` after a jump, meant for the sidebar, closed the whole viewer. `q` still closes at once. Over the page, the sidebar has the focus while it is shown, and its own `Esc` hides it.
- While the sidebar has the focus, the footer shows its keys (`type: filter · ↑/↓: select · wheel: scroll · Enter or click: jump · Esc: hide`). Otherwise the default hints of a library page add `s: sidebar`; while the sidebar stands beside the page, the hints name `Esc: hide sidebar` and `q` as the close key.

### D5: The filter matches like `robotcode doc keywords`

The filter text is matched with Robot Framework's `MultiMatcher([f"*{text}*"], ignore="_")`, as `doc keywords` matches patterns (`doc-cli` D7): contains, `*` and `?`, case and spaces ignored, underscores ignored. A level-2 entry is listed while it matches or one of its level-3 entries does, so the grouping stays visible. After each change of the text, the selection moves to the first entry that matches itself, so it skips a level-2 entry that is only listed for its entries: `get match count` selects the keyword, not `Keywords` (found during implementation). An empty filter lists everything and selects the first entry.

### D6: Showing or hiding side by side keeps the heading at the top

Showing or hiding the sidebar side by side changes the body's width, so the page is reflowed at the new width. The render cache applies, so going back to a width seen before is cheap. Unlike a resize, the scroll position is kept by heading rather than by percentage: before the reflow, the last heading at or above the top line and the distance to it are taken from `_anchor_to_line`. After the reflow, the page is scrolled to that heading's new line. A search query is run again on the new rendering, so its matches stay. The back/forward history and the focused link are dropped, as on a resize, because their positions belong to the old width. On top, the width does not change and nothing is reflowed.

Rejected: mapping the back/forward history to the new width. Every entry would have to be re-located by heading. The resize rule already accepts the loss, and the sidebar is usually shown once and left open.

## Risks / Trade-offs

- [The first reflow after showing the sidebar side by side takes as long as rendering the page at a new width] → It happens once per width; the render cache serves the next toggles.
- [Showing or hiding the sidebar side by side drops the back/forward history] → The same rule as a resize, and jumps made from the sidebar are recorded again. The heading at the top stays in place (D6).
- [On top, the sidebar covers the left part of the page while it is open] → It closes after a jump and with `Esc`.
- [A level-2 heading inside keyword or type documentation would appear as a section] → Keyword and type documentation start at level 5 on the page (`doc-cli` D4 and its review corrections), so only the page's own sections, keywords and data types are entries.

## Migration Plan

New behaviour behind a key; no configuration or data migration. Apply after `doc-cli`. Rollback is a revert.
