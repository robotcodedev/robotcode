"""Full-screen markdown viewer — a standalone prompt_toolkit Application.

Runs in the terminal's alternate-screen buffer (`less` / `man` /
`vim` style), so the host prompt and its scrollback survive the
viewer's lifetime untouched. Markdown is rendered via `rich`,
captured to an ANSI string, and parsed into `(style, text)`
fragments that the viewer can paint and post-process for search
and link highlights.

Interactive features:

- **Search** (``/``): less-style — type, Enter to execute, ``n`` /
  ``N`` to walk matches. All hits stay highlighted, current one
  brighter.
- **Links**: rich emits OSC 8 link metadata around link text; we
  strip the escapes (prompt_toolkit's ANSI parser doesn't grok
  OSC) and keep the spans for navigation. ``Tab`` / ``Shift-Tab``
  cycle, ``f`` or ``Enter`` follows — ``#anchor`` jumps to the
  matching section, ``http(s)://`` opens in the browser.
- **Back/forward** (``[`` / ``]``): browser-style stack of anchor
  jumps within the doc.
- **Sidebar** (``s``, library pages only): the level-2 and level-3
  headings of the page with a filter field; side by side with the
  page in a wide terminal, over it in a narrow one.
- **Resize**: terminal width changes trigger a debounced reflow
  that re-renders the markdown at the new width; per-width
  snapshots are cached so re-resizes are instant.
"""

import asyncio
import re
import webbrowser
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI, StyleAndTextTuples, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.styles import Style
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import Frame
from rich.console import Console
from rich.markdown import Markdown
from robot.utils import MultiMatcher

from robotcode.robot.utils.markdown_docs import heading_anchors


def render_markdown_to_ansi(text: str, *, width: int = 80) -> str:
    """Render `text` as markdown via `rich`, capture to ANSI string.

    Convenience wrapper around `render_markdown_for_viewer` that drops
    the link spans. Used by tests and any caller that only cares about
    a rendered ANSI string with the OSC 8 hyperlink sequences stripped
    out.
    """
    ansi, _spans = render_markdown_for_viewer(text, width=width)
    return ansi


def render_markdown_for_viewer(text: str, *, width: int = 80) -> Tuple[str, List[Tuple[int, int, str]]]:
    """Render markdown via `rich` and return ``(ansi_text, link_spans)``.

    - ``soft_wrap=False`` (the rich default) makes `rich` hard-wrap
      paragraphs, code blocks, list items, and tables at word
      boundaries — *not* the terminal-controlled soft wrap. Without
      this every line longer than ``width`` flowed off the right
      edge because soft_wrap defers wrapping to the surrounding
      terminal, which in the doc viewer is `prompt_toolkit`'s
      buffer and doesn't reflow text.
    - We *keep* `rich`'s default ``hyperlinks=True``: rich emits OSC 8
      sequences (``\\x1b]8;…;url\\x1b\\\\link text\\x1b]8;;\\x1b\\\\``)
      around link text. The URL lives entirely in the OSC parameters —
      no ``(url)`` clutter follows the link text inline.
      `_strip_osc8_hyperlinks` then removes those escape sequences
      from the ANSI body (prompt_toolkit's ANSI parser doesn't grok
      OSC and would otherwise paint them as visible garbage) and
      captures each ``(start, end, url)`` span so the viewer can
      paint a link style on the text and let the user Tab through
      to follow them.

    Returns ``("", [])`` for empty input so the caller doesn't need to
    pre-check.
    """
    if not text:
        return "", []
    # The ANSI text goes to `_strip_osc8_hyperlinks` and prompt_toolkit, never to a console.
    # On Windows without a console that supports VT sequences, such as in CI, `rich` would
    # assume a legacy console and leave out the OSC 8 links.
    console = Console(width=width, record=False, soft_wrap=False, force_terminal=True, legacy_windows=False)
    with console.capture() as cap:
        console.print(Markdown(text))
    return _strip_osc8_hyperlinks(cap.get())


# OSC 8 sequences mark hyperlinks. Open form:
#   ESC ] 8 ; params ; url BEL
#   ESC ] 8 ; params ; url ESC \
# Close form: same with empty url.
# (BEL is `\x07`, ESC is `\x1b`, ESC \\ is the standard string terminator.)
_OSC8_RE = re.compile(r"\x1b\]8;[^;]*;([^\x07\x1b]*)(?:\x07|\x1b\\)")

# SGR (Select Graphic Rendition) — colour/style escapes. Matters for
# the OSC stripper because SGR doesn't advance "visible position" and
# we copy it through to the output for prompt_toolkit's ANSI parser.
_SGR_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _strip_osc8_hyperlinks(ansi: str) -> Tuple[str, List[Tuple[int, int, str]]]:
    """Remove OSC 8 hyperlink sequences from ``ansi``; return cleaned
    ANSI + the link spans in visible-text coordinates.

    Visible-text coordinates = the position you'd get from
    "strip every ANSI escape, count chars". That's the coordinate
    space the viewer uses for search matches and link overlays, so
    the spans returned here drop straight into `self._links` and
    are ready for ``_overlay_match_highlight`` / ``_anchor_to_line``
    lookups.

    Implementation note: iterates OSC 8 matches in one ``finditer``
    pass and slices the text between them, rather than walking
    char-by-char with ``regex.match`` (~14x faster on a typical
    library doc). SGR escapes inside each between-OSC chunk get
    a separate ``finditer`` pass to deduct their length from the
    visible position counter — those don't show on screen.
    """
    spans: List[Tuple[int, int, str]] = []
    pending: Optional[Tuple[int, str]] = None
    out: List[str] = []
    last_end = 0
    visible_pos = 0
    for m in _OSC8_RE.finditer(ansi):
        chunk = ansi[last_end : m.start()]
        out.append(chunk)
        # Visible chars in the chunk = total minus the bytes spent on SGR escapes.
        sgr_chars = sum(sm.end() - sm.start() for sm in _SGR_RE.finditer(chunk))
        visible_pos += len(chunk) - sgr_chars

        url = m.group(1)
        if url:
            pending = (visible_pos, url)
        elif pending is not None:
            spans.append((pending[0], visible_pos, pending[1]))
            pending = None
        last_end = m.end()
    out.append(ansi[last_end:])
    return "".join(out), _coalesce_link_spans(spans)


# Max whitespace gap (newline + maybe a couple of pad chars from the
# Frame border / list indent) between two OSC 8 spans before we treat
# them as separate links rather than one wrapped link.
_WRAP_GAP_TOLERANCE = 4

# Lines of context kept above a `scroll_to` target so it opens clearly visible
# (mid-file, with a little preceding context) rather than jammed at the top edge.
_SCROLL_TO_CONTEXT = 3

# The sidebar's width, including its border to the page. It stands beside the
# page when the page keeps at least `_MIN_PAGE_WIDTH_BESIDE_SIDEBAR` columns,
# and lies over the page in a narrower terminal.
_SIDEBAR_WIDTH = 32
_MIN_PAGE_WIDTH_BESIDE_SIDEBAR = 60


def _coalesce_link_spans(spans: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
    """Merge adjacent spans that point to the same URL.

    `rich` emits two separate OSC 8 sequences when a markdown link's
    text wraps across a line break — the user sees one logical link
    but ``Tab`` would land on each piece in turn. Merging them so
    Tab only stops once per *logical* link is the natural UX.
    """
    if not spans:
        return spans
    out: List[Tuple[int, int, str]] = [spans[0]]
    for span in spans[1:]:
        s, e, url = span
        prev_s, prev_e, prev_url = out[-1]
        if url == prev_url and s - prev_e <= _WRAP_GAP_TOLERANCE:
            out[-1] = (prev_s, e, prev_url)
        else:
            out.append(span)
    return out


def _compute_link_lines(plain: str, links: List[Tuple[int, int, str]]) -> List[int]:
    """0-based source line of each link's start position in ``plain``.

    Single forward sweep so the cost is O(len(plain) + len(links)).
    The naïve ``plain.count("\\n", 0, start)`` per link is O(n*m) and
    measurably slow on long docs — for a typical library doc that's
    ~12ms shaved off every reflow.
    """
    result: List[int] = []
    cursor = 0
    line = 0
    for start, _e, _t in links:
        if start > cursor:
            line += plain.count("\n", cursor, start)
            cursor = start
        result.append(line)
    return result


_HELP_HINTS = (
    " j/k or ↑/↓ or wheel: scroll · /: search · Tab or click: links · "
    "[/]: back/forward · Shift+drag: select · q/Esc/Enter: close "
)

_OUTLINE_HELP_HINTS = (
    " j/k or ↑/↓ or wheel: scroll · s: sidebar · /: search · Tab or click: links · "
    "[/]: back/forward · Shift+drag: select · q/Esc/Enter: close "
)

# While the sidebar stands beside the page, `Esc` on the page hides it first.
_SIDEBAR_SHOWN_HELP_HINTS = (
    " Esc: hide sidebar · s: focus sidebar · j/k or ↑/↓ or wheel: scroll · /: search · "
    "Tab or click: links · [/]: back/forward · q/Enter: close "
)

_SIDEBAR_HINTS = " type: filter · ↑/↓: select · wheel: scroll · Enter or click: jump · Esc: hide "

# The rendered-line lookup runs a heading's title through `_strip_md_emphasis`
# because `rich` consumes those markers when it paints.

_MD_EMPHASIS_RE = re.compile(r"[*_`]")


def _strip_md_emphasis(text: str) -> str:
    """Drop `*`, `_`, `` ` `` markers — `rich` consumes them in rendering."""
    return _MD_EMPHASIS_RE.sub("", text)


def _build_anchor_to_line_map(md_source: str, rendered_plain: str) -> Dict[str, int]:
    """Map each header's anchor slug to the 0-based rendered line where
    its title text appears.

    Walks markdown headers in source order and the rendered output line
    by line in parallel; for each header, locates the first rendered
    line equal to the header's display text (emphasis-stripped) at or
    after the current cursor. Source order matches rendered order
    because `rich` preserves the structure of the markdown.

    Returns `{}` if anchor extraction fails for any reason — the
    `Tab`-cycle still works (browser-open for HTTPS still works), only
    in-doc jump becomes a no-op.
    """
    rendered_lines = rendered_plain.split("\n")
    result: Dict[str, int] = {}
    cursor = 0
    # `heading_anchors` skips `#` lines of fenced code blocks, which are no headings,
    # and numbers repeated anchors as the links of the page do
    for _, raw_title, anchor in heading_anchors(md_source):
        display = _strip_md_emphasis(raw_title)
        for j in range(cursor, len(rendered_lines)):
            if rendered_lines[j].strip() == display:
                result[anchor] = j
                cursor = j + 1
                break
    return result


class _OutlineEntry(NamedTuple):
    """One heading in the sidebar: its level (2 or 3), its title as the page shows it, and its anchor."""

    level: int
    title: str
    anchor: str


def _build_outline(md_source: str, anchor_to_line: Dict[str, int]) -> List[_OutlineEntry]:
    """The level-2 and level-3 headings of ``md_source``, in document order.

    Headings without a rendered line are left out, because the sidebar
    jumps through the anchor map.
    """
    return [
        _OutlineEntry(level, _strip_md_emphasis(title), anchor)
        for level, title, anchor in heading_anchors(md_source)
        if level in (2, 3) and anchor in anchor_to_line
    ]


def _fit(text: str, width: int) -> str:
    """``text`` padded to ``width`` columns, or cut with `…` when it is longer."""
    if get_cwidth(text) > width:
        while get_cwidth(text) > width - 1:
            text = text[:-1]
        text += "…"
    return text + " " * (width - get_cwidth(text))


class _RenderSnapshot(NamedTuple):
    """Full set of derived data from one markdown render at a given width.

    Cached by `DocViewer._render_cache` keyed on body width so a
    resize back to a previously-seen width is a dict lookup + state
    swap instead of another rich render (~300-400ms for a typical
    library doc). All five fields are derived from the same render
    pass and must stay in sync — bundling them in one snapshot
    avoids the "is this still the same render?" question.
    """

    fragments: StyleAndTextTuples
    plain: str
    links: List[Tuple[int, int, str]]
    link_lines: List[int]
    anchor_to_line: Dict[str, int]


class _NavState(NamedTuple):
    """One entry in the back / forward navigation stacks.

    Captures everything needed to return to a position the user was at:
    the document itself (`title` + `md_source`) plus the scroll offset
    and focused link. Carrying the source means a follow that loaded a
    *different* document — e.g. a keyword page opened from a list — can
    be reversed by reloading the previous document, not just scrolling.
    `outline` tells whether that document has a sidebar.
    """

    title: str
    md_source: str
    scroll: int
    current_link: int
    outline: bool = False


# Viewer-only style entries. The host interpreter's `_DEFAULT_STYLE`
# is for the prompt + log output; the viewer is its own Application
# with its own narrow palette, so we don't grow `_pt.components` for
# a couple of classes that only the viewer ever paints with.
_VIEWER_STYLE = Style.from_dict(
    {
        "doc.footer": "fg:#7f7f7f",
        "doc.footer.count": "fg:#5fafd7 bold",
        "doc.footer.nomatch": "fg:#d7af00",
        "doc.search.prompt": "fg:#5fafd7 bold",
        "doc.match": "reverse",
        "doc.match.current": "reverse bold",
        "doc.sidebar.border": "fg:#7f7f7f",
        "doc.sidebar.section": "bold",
        "doc.sidebar.selected": "reverse",
        "doc.sidebar.empty": "fg:#7f7f7f",
    }
)


def _fragments_text(fragments: StyleAndTextTuples) -> str:
    """Concatenate the text portion of a fragment list.

    Used to derive the plain string we search against from the
    rich-rendered ANSI body.
    """
    return "".join(text for _style, text, *_ in fragments)


def _coalesce_fragments(fragments: StyleAndTextTuples) -> StyleAndTextTuples:
    """Merge runs of consecutive fragments that share the same style.

    `rich`'s ANSI output produces one fragment per styled segment —
    for a typical Robot library doc this is hundreds of thousands of
    micro-fragments (`BuiltIn` ≈ 190k). prompt_toolkit walks the full
    list on every render to split into lines, so without coalescing
    each j/k keypress drags. Merging runs with identical styles
    shrinks the list ~14x and makes scrolling snappy again.

    Three-tuple fragments (style, text, mouse_handler) are passed
    through unchanged — `rich`'s output uses only 2-tuples, but the
    `StyleAndTextTuples` contract allows 3-tuples and we shouldn't
    silently drop the third slot if it ever appears.
    """
    if not fragments:
        return fragments
    out: StyleAndTextTuples = []
    last_style: Optional[str] = None
    parts: List[str] = []
    for frag in fragments:
        if len(frag) > 2:
            # Flush the buffered run and pass the 3-tuple through.
            if last_style is not None:
                out.append((last_style, "".join(parts)))
                parts = []
                last_style = None
            out.append(frag)
            continue
        style, text = frag[0], frag[1]
        if style == last_style:
            parts.append(text)
        else:
            if last_style is not None:
                out.append((last_style, "".join(parts)))
            last_style = style
            parts = [text]
    if last_style is not None:
        out.append((last_style, "".join(parts)))
    return out


def _emit(out: StyleAndTextTuples, style: str, text: str, handler: Optional[Callable[[MouseEvent], object]]) -> None:
    """Append a 2- or 3-tuple fragment depending on whether a handler is set."""
    if not text:
        return
    if handler is None:
        out.append((style, text))
    else:
        out.append((style, text, handler))


def _overlay_match_highlight(
    fragments: StyleAndTextTuples,
    matches: List[Tuple[int, int]],
    current_idx: int,
) -> StyleAndTextTuples:
    """Return a new fragment list with matches styled by `class:doc.match`
    (and the current match by `class:doc.match.current`).

    Walks the original fragments and the sorted match list in lockstep,
    splitting any fragment that overlaps a match. The base style is
    preserved — prompt_toolkit's style engine merges the appended
    class on top, so colours from `rich` survive but a `reverse`
    attribute lights up the match. Any existing mouse handler on a
    source 3-tuple fragment is inherited by every split-out segment,
    so link click targets stay clickable while search highlights are
    drawn over them.
    """
    if not matches:
        return list(fragments)

    out: StyleAndTextTuples = []
    pos = 0  # offset into the plain (concatenated) text
    match_iter = iter(enumerate(matches))
    current = next(match_iter, None)

    for frag in fragments:
        style, text = frag[0], frag[1]
        handler = frag[2] if len(frag) > 2 else None
        text_len = len(text)
        i = 0
        while i < text_len:
            # Drop matches that lie entirely before the current cursor.
            while current is not None and current[1][1] <= pos + i:
                current = next(match_iter, None)
            if current is None:
                _emit(out, style, text[i:], handler)
                i = text_len
                break
            m_idx, (m_start, m_end) = current
            if pos + i < m_start:
                # Unmatched run up to the next match.
                seg = min(m_start - (pos + i), text_len - i)
                _emit(out, style, text[i : i + seg], handler)
                i += seg
            else:
                # Inside the match — overlay the highlight class.
                seg = min(m_end - (pos + i), text_len - i)
                highlight_class = "class:doc.match.current" if m_idx == current_idx else "class:doc.match"
                _emit(out, f"{style} {highlight_class}", text[i : i + seg], handler)
                i += seg
        pos += text_len
    return out


def _attach_link_handlers(
    fragments: StyleAndTextTuples,
    links: List[Tuple[int, int, str]],
    handler_factory: Callable[[int], Callable[[MouseEvent], object]],
) -> StyleAndTextTuples:
    """Return a new fragment list with each link span wrapped in a
    3-tuple carrying the per-link mouse handler.

    Walks fragments and links in lockstep, splitting fragments that
    overlap a link boundary. Called once per snapshot (in
    `_build_render_snapshot`), so the per-render path stays cheap —
    `_overlay_match_highlight` then inherits each handler through
    its own splits.
    """
    if not links:
        return list(fragments)

    out: StyleAndTextTuples = []
    pos = 0
    link_iter = iter(enumerate(links))
    current = next(link_iter, None)

    for frag in fragments:
        style, text = frag[0], frag[1]
        base_handler = frag[2] if len(frag) > 2 else None
        text_len = len(text)
        i = 0
        while i < text_len:
            while current is not None and current[1][1] <= pos + i:
                current = next(link_iter, None)
            if current is None:
                _emit(out, style, text[i:], base_handler)
                i = text_len
                break
            l_idx, (l_start, l_end, _target) = current
            if pos + i < l_start:
                seg = min(l_start - (pos + i), text_len - i)
                _emit(out, style, text[i : i + seg], base_handler)
                i += seg
            else:
                seg = min(l_end - (pos + i), text_len - i)
                _emit(out, style, text[i : i + seg], handler_factory(l_idx))
                i += seg
        pos += text_len
    return out


class DocViewer:
    """Markdown viewer running as a separate fullscreen Application.

    The layout (body Window + sidebar + search bar + footer + Frame) is
    built once at construction; `run(title, markdown)` swaps in the new
    content, resets scroll + search state, and invokes
    `Application.run()`. The app is set to `full_screen=True` so
    prompt_toolkit switches to the terminal's alternate screen buffer
    for the duration — same trick `less` / `vim` use, so the host
    prompt's scrollback is undisturbed.
    """

    def __init__(
        self,
        link_resolver: Optional[Callable[[str], Optional[Tuple[str, str]]]] = None,
    ) -> None:
        # Resolves a followed link target that is neither an `#anchor`
        # nor an `http(s)://` URL into new `(title, markdown)` content,
        # loaded in place. Used to open a keyword's page from a list.
        self._link_resolver = link_resolver
        self._title = ""

        # Body content: stored as fragments so we can re-render with
        # search highlights overlaid. `_plain` is the concatenation
        # used for case-insensitive substring search.
        self._fragments: StyleAndTextTuples = []
        self._plain: str = ""

        # Search state.
        self._in_search_mode = False
        self._search_query = ""
        self._matches: List[Tuple[int, int]] = []  # (start, end) into `_plain`
        self._current_match = -1  # index into `_matches`; -1 = none

        # Link-navigation state. `_links` are `(start, end, target)`
        # triples in `_plain` coordinates (start/end span the link
        # text itself, courtesy of `_strip_osc8_hyperlinks`).
        # `_link_lines[i]` caches the 0-based source line of
        # `_links[i].start` so Tab-cycling doesn't pay a fresh
        # `_plain.count("\n", …)` per keypress on long docs.
        # `_current_link` is -1 when no link is focused — Tab cycles
        # it forward, Shift-Tab backward. `_anchor_to_line` maps
        # `#anchor` targets to 0-based rendered line indices for
        # in-doc jumps.
        self._links: List[Tuple[int, int, str]] = []
        self._link_lines: List[int] = []
        self._current_link = -1
        self._anchor_to_line: Dict[str, int] = {}

        # Browser-style back / forward stacks for `#anchor` jumps and
        # in-place content follows (see `_NavState`). Search state is
        # intentionally untouched on back/forward (going back shouldn't
        # drop the user's current search). External URL follows don't
        # push since the viewer itself doesn't move.
        self._back_stack: List[_NavState] = []
        self._forward_stack: List[_NavState] = []

        # Resize state. `_md_source` keeps the markdown around so we
        # can re-render at the new width when the terminal resizes.
        # Re-rendering BuiltIn takes ~300-400ms, so we debounce: each
        # render pass checks the width and (re-)schedules a reflow
        # 150ms in the future; during a fast drag-resize that ends
        # up running just once, after the user stops.
        #
        # `_render_cache` keeps fully-built fragment sets keyed by
        # body width — resizing back to a previously-seen width
        # (e.g. user shrinks and re-expands the window) is then a
        # cheap dict lookup + state swap instead of another rich
        # render. The cache is cleared on every new `.doc` call
        # because all entries are keyed to a single markdown source.
        self._md_source: str = ""
        self._last_body_width: int = 0
        self._resize_task: Optional[asyncio.TimerHandle] = None
        self._render_cache: Dict[int, _RenderSnapshot] = {}

        # Sidebar state. Only a document loaded with `outline=True` has an
        # outline. `_listed` holds the indices of the entries the filter
        # lists, `_selected` the selected row of that list (-1 = none).
        self._with_outline = False
        self._outline: List[_OutlineEntry] = []
        self._listed: List[int] = []
        self._selected = -1
        self._sidebar_visible = False

        # Pin the control's "cursor" to the top of the visible area so
        # `Window._scroll_without_linewrapping` doesn't clamp
        # `vertical_scroll` back to 0 — its do_scroll() resets the
        # scroll any time the cursor would fall outside the visible
        # window, and `FormattedTextControl`'s default cursor sits at
        # line 0. Tracking the scroll keeps the cursor visible so the
        # algorithm leaves our scroll value alone.
        self._body_control = FormattedTextControl(
            text=self._compute_body_fragments,
            focusable=True,
            show_cursor=False,
            get_cursor_position=lambda: Point(x=0, y=self._body_window.vertical_scroll),
        )
        # `wrap_lines=False` because `rich` already word-wraps the
        # markdown body to the width we pass it (see
        # `render_markdown_to_ansi` — `soft_wrap=False` makes rich
        # hard-wrap at word boundaries for paragraphs, code blocks,
        # lists, and tables). prompt_toolkit's own `wrap_lines`
        # implementation cuts mid-word, which is exactly the
        # behaviour the user complained about; rich's word-aware
        # wrap is what we want.
        self._body_window = Window(content=self._body_control, wrap_lines=False, always_hide_cursor=True)

        # Search input — a single-line Buffer below the body. Enter
        # commits the search via `_execute_search`; Esc cancels via the
        # control-local key bindings (see `_build_search_bindings`).
        self._search_buffer = Buffer(multiline=False, accept_handler=self._on_search_accept)
        self._search_control = BufferControl(
            buffer=self._search_buffer,
            key_bindings=self._build_search_bindings(),
        )
        # The visible prefix in front of the search input ("/") plus
        # the live input field. We render them side by side via a
        # 2-window VSplit-like layout — but a single Window with two
        # FormattedTextControls is simpler if we use a prefix in the
        # footer. Easiest: a 1-line HSplit row with two windows.
        self._search_prefix_window = Window(
            content=FormattedTextControl(text=lambda: [("class:doc.search.prompt", "/")]),
            width=1,
            height=1,
        )
        self._search_window = Window(content=self._search_control, height=1)

        # Footer — either the help hints or the match count, depending
        # on whether a search is active. Hidden while the search bar
        # is open so the bar gets the bottom row to itself.
        self._footer_control = FormattedTextControl(text=self._compute_footer_text)
        self._footer_window = Window(content=self._footer_control, height=1, style="class:doc.footer")

        # Sidebar — a filter field above the list of headings, with a
        # border to the page. Like the body, the list pins its "cursor" to
        # the top of the visible area, so the mouse wheel scrolls it freely;
        # `_scroll_selection_into_view` keeps a moved selection visible.
        self._filter_buffer = Buffer(multiline=False, on_text_changed=lambda _buf: self._apply_filter())
        self._filter_window = Window(
            content=BufferControl(buffer=self._filter_buffer, key_bindings=self._build_sidebar_bindings()),
            height=1,
        )
        self._outline_window = Window(
            content=FormattedTextControl(
                text=self._compute_outline_fragments,
                show_cursor=False,
                get_cursor_position=lambda: Point(x=0, y=self._outline_window.vertical_scroll),
            ),
            always_hide_cursor=True,
        )
        filter_row = VSplit(
            [
                Window(content=FormattedTextControl([("class:doc.search.prompt", " Filter: ")]), width=9, height=1),
                self._filter_window,
            ]
        )
        self._sidebar = VSplit(
            [
                HSplit(
                    [filter_row, Window(height=1, char="─", style="class:doc.sidebar.border"), self._outline_window]
                ),
                Window(width=1, char="│", style="class:doc.sidebar.border"),
            ],
            width=_SIDEBAR_WIDTH,
        )
        # The two places of a shown sidebar; `_main_area` picks one, or the
        # body alone, so the layout only ever holds one of them.
        self._sidebar_beside_area = VSplit([self._sidebar, self._body_window])
        self._sidebar_over_area = FloatContainer(
            content=self._body_window,
            floats=[Float(content=self._sidebar, left=0, top=0, bottom=0, width=_SIDEBAR_WIDTH)],
        )

        search_row = VSplit([self._search_prefix_window, self._search_window])
        frame_body = HSplit(
            [
                DynamicContainer(self._main_area),
                ConditionalContainer(search_row, filter=Condition(lambda: self._in_search_mode)),
                ConditionalContainer(self._footer_window, filter=Condition(lambda: not self._in_search_mode)),
            ]
        )
        self._frame = Frame(body=frame_body, title=lambda: self._title)

        # One reusable Application — `run()` rebinds the title and
        # body text before each invocation.
        #
        # `mouse_support=True` so links become clickable and the wheel
        # scrolls the body. Terminal-native drag-selection still works
        # in every mainstream terminal (iTerm2, Kitty, Alacritty,
        # GNOME-Terminal, Windows Terminal) by holding **Shift** while
        # dragging — that pass-through is the standard TUI convention
        # (htop, fzf, lazygit). The footer surfaces the hint.
        self._app: Application[None] = Application(
            layout=Layout(self._frame, focused_element=self._body_window),
            key_bindings=self._build_key_bindings(),
            style=_VIEWER_STYLE,
            full_screen=True,
            mouse_support=True,
        )
        # Re-apply a `scroll_to` target after the first render (see
        # `_apply_pending_scroll`). Registered once — the app is reused across
        # `run()` calls — and gated on `self._pending_scroll` so it no-ops
        # unless a fresh `run(scroll_to=…)` armed it.
        self._pending_scroll: Optional[str] = None
        self._app.after_render += self._apply_pending_scroll

    def run(self, title: str, markdown: str, *, scroll_to: Optional[str] = None, outline: bool = False) -> None:
        """Render ``markdown`` into the body and run the viewer fullscreen.

        Blocks until the user presses Esc / q / Enter. Uses the alt
        screen buffer, so the host prompt's terminal state survives
        the call untouched. ``scroll_to`` opens the viewer scrolled to the
        first rendered line containing that text (e.g. a marked source line).
        ``outline`` gives the document a sidebar with its headings, for the
        page of a library, resource file or suite file.
        """
        # A fresh top-level invocation starts with empty history.
        self._back_stack = []
        self._forward_stack = []
        self._load_document(title, markdown, scroll_to=scroll_to, outline=outline)
        # The pre-render scroll above gets reset by the first render; arm the
        # `after_render` hook to re-apply it once the body is really on screen.
        self._pending_scroll = scroll_to

        try:
            self._app.run()
        finally:
            # Don't leak a pending reflow callback into the next
            # `.doc` invocation — if it fired against a closed app
            # the invalidate() at the end would be a no-op, but the
            # state shuffle would still run.
            if self._resize_task is not None:
                self._resize_task.cancel()
                self._resize_task = None

    def _load_document(
        self, title: str, markdown: str, *, scroll_to: Optional[str] = None, outline: bool = False
    ) -> None:
        """Adopt ``markdown`` as the current document and reset per-doc
        state (scroll, focused link, search, sidebar). Leaves the back /
        forward stacks alone so it can be reused for in-place link follows;
        `run` clears them for a fresh top-level invocation. ``scroll_to``
        opens scrolled to the first rendered line containing that text.
        ``outline`` gives the document a sidebar, hidden at first.
        """
        self._title = title
        self._md_source = markdown
        # New doc → all cached renders are for the OLD markdown. Wipe.
        self._render_cache = {}
        self._with_outline = outline
        self._sidebar_visible = False
        if self._sidebar_has_focus():
            self._app.layout.focus(self._body_window)
        self._render_at_width(self._body_width())

        self._outline = _build_outline(markdown, self._anchor_to_line) if outline else []
        self._filter_buffer.reset()
        self._apply_filter()

        self._current_link = -1
        self._in_search_mode = False
        self._search_query = ""
        self._matches = []
        self._current_match = -1
        self._search_buffer.reset()
        self._body_window.vertical_scroll = 0
        if scroll_to:
            self._scroll_to_text(scroll_to)

    def _scroll_to_text(self, text: str) -> None:
        """Scroll so the first rendered line containing ``text`` is visible near
        the top, with a few lines of context above. Leaves the scroll untouched
        if the text isn't present. Mirrors anchor-follow's clamping (`_max_scroll`
        is 0 before the first render, so set the raw value and let render clamp)."""
        for idx, rendered_line in enumerate(self._plain.split("\n")):
            if text in rendered_line:
                target = max(0, idx - _SCROLL_TO_CONTEXT)
                max_scroll = self._max_scroll()
                self._body_window.vertical_scroll = min(target, max_scroll) if max_scroll else target
                return

    def _apply_pending_scroll(self, _app: object) -> None:
        """`after_render` hook: re-apply a pending `scroll_to` once, after the
        first real render. The pre-render scroll set in `_load_document` is reset
        by prompt_toolkit's first render (the cursor-pin only protects the scroll
        once render-info exists), so the target must be re-applied here — when
        `self._plain` reflects the real terminal width and `_max_scroll` is valid."""
        if self._pending_scroll is None:
            return
        target = self._pending_scroll
        self._pending_scroll = None
        self._scroll_to_text(target)
        self._app.invalidate()

    def _current_state(self) -> _NavState:
        """Snapshot the current document + position for the nav stacks."""
        return _NavState(
            self._title, self._md_source, self._body_window.vertical_scroll, self._current_link, self._with_outline
        )

    def _restore_state(self, state: _NavState) -> None:
        """Return to a `_NavState`, reloading its document first if the
        current one differs."""
        if state.md_source != self._md_source:
            self._load_document(state.title, state.md_source, outline=state.outline)
        self._body_window.vertical_scroll = state.scroll
        self._current_link = state.current_link

    def _render_at_width(self, body_width: int) -> None:
        """Render the markdown at ``body_width`` and adopt the result.

        Cache hit → state swap, no work. Cache miss → build a fresh
        snapshot, store it, then adopt. Either way the body, plain
        text, link spans, line cache and anchor map move atomically.
        """
        self._last_body_width = body_width
        snapshot = self._render_cache.get(body_width)
        if snapshot is None:
            snapshot = self._build_render_snapshot(body_width)
            self._render_cache[body_width] = snapshot
        self._fragments = snapshot.fragments
        self._plain = snapshot.plain
        self._links = snapshot.links
        self._link_lines = snapshot.link_lines
        self._anchor_to_line = snapshot.anchor_to_line

    def _build_render_snapshot(self, body_width: int) -> _RenderSnapshot:
        """Run the full render → fragments → indices pipeline for one width.

        `render_markdown_for_viewer` strips `rich`'s OSC 8 hyperlink
        sequences and returns link spans separately, so the URLs
        never show up as visible body text. ``to_formatted_text(ANSI)``
        produces tens of thousands of micro-fragments which we
        coalesce by style — without that pass each keypress walks
        a 200k-element list. Anchor + link-line indices ride along
        so `f`/Tab can navigate without re-scanning the body.
        """
        ansi_text, links = render_markdown_for_viewer(self._md_source, width=body_width)
        fragments = _coalesce_fragments(list(to_formatted_text(ANSI(ansi_text))))
        plain = _fragments_text(fragments)
        fragments = _attach_link_handlers(fragments, links, self._make_link_click_handler)
        return _RenderSnapshot(
            fragments=fragments,
            plain=plain,
            links=links,
            link_lines=_compute_link_lines(plain, links),
            anchor_to_line=_build_anchor_to_line_map(self._md_source, plain),
        )

    def _check_resize(self) -> None:
        """If the terminal width changed, schedule a debounced reflow.

        Called from `_compute_body_fragments` (every render). Detects
        a width change by comparing the current `output` size to the
        width we last rendered at; on a difference, (re-)schedules
        ``_reflow_after_resize`` 150ms in the future via the running
        asyncio loop. Drag-resizing a terminal emits many resize
        events in quick succession — debouncing collapses them into
        one re-render after the drag settles, so the user doesn't
        see ~300ms of stalled flicker for every column delta.
        """
        if not self._md_source:
            return
        # Over the page, the sidebar is only shown while it has the focus. After
        # a resize that leaves no room beside the page while the page has the
        # focus, it would cover the page, so it is hidden.
        if (
            self._sidebar_visible
            and not self._sidebar_has_focus()
            and not self._sidebar_beside(self._app.output.get_size().columns)
        ):
            self._sidebar_visible = False
            self._app.invalidate()
        body_width = self._body_width()
        if body_width == self._last_body_width:
            return
        if self._resize_task is not None:
            self._resize_task.cancel()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (shouldn't happen during app.run, but
            # defensive — fall back to a synchronous reflow).
            self._reflow_after_resize(body_width)
            return
        self._resize_task = loop.call_later(0.15, self._reflow_after_resize, body_width)

    def _reflow_after_resize(self, body_width: int) -> None:
        """Re-render at the new width, preserve scroll roughly, drop
        position-dependent state.

        Search matches + back/forward + focused link all point into
        the old `_plain` coordinates — reflowing invalidates them.
        Rather than re-mapping (each one would need fuzzy locate),
        we clear them. The scroll position is preserved as a *line
        percentage* of the old content; close enough that the user
        stays near where they were reading.
        """
        self._resize_task = None
        if body_width == self._last_body_width:
            return  # already at the target width (raced with another reflow)

        old_lines = max(1, self._plain.count("\n") + 1)
        scroll_pct = self._body_window.vertical_scroll / old_lines

        self._render_at_width(body_width)

        new_lines = max(1, self._plain.count("\n") + 1)
        self._body_window.vertical_scroll = max(0, min(int(scroll_pct * new_lines), new_lines - 1))

        # Position-dependent state is now stale — drop it. The user
        # has to re-search after a resize, but at least the indices
        # never silently point at the wrong characters.
        self._current_link = -1
        self._back_stack = []
        self._forward_stack = []
        self._matches = []
        self._current_match = -1

        self._app.invalidate()

    # ------------------------------------------------------------------
    # Sidebar.
    # ------------------------------------------------------------------

    def _sidebar_beside(self, columns: int) -> bool:
        """Whether a shown sidebar stands beside the page in a terminal ``columns`` wide."""
        return columns - 2 - _SIDEBAR_WIDTH >= _MIN_PAGE_WIDTH_BESIDE_SIDEBAR

    def _body_width(self) -> int:
        """The width the page is rendered at: the terminal's, less the frame
        border (1 char on each side) and a sidebar beside the page."""
        columns = self._app.output.get_size().columns
        if self._sidebar_visible and self._sidebar_beside(columns):
            return columns - 2 - _SIDEBAR_WIDTH
        return max(columns - 2, 40)

    def _sidebar_has_focus(self) -> bool:
        return self._app.layout.current_window is self._filter_window

    def _main_area(self) -> Container:
        """The body, with the sidebar beside it or over it while it is shown."""
        if not self._sidebar_visible:
            return self._body_window
        if self._sidebar_beside(self._app.output.get_size().columns):
            return self._sidebar_beside_area
        return self._sidebar_over_area

    def _show_sidebar(self) -> None:
        """Show the sidebar, select the heading at the top of the page and focus the filter field."""
        if not self._sidebar_visible:
            self._sidebar_visible = True
            self._reflow_for_sidebar()
        self._select_entry_at_top()
        self._app.layout.focus(self._filter_window)

    def _hide_sidebar(self) -> None:
        self._sidebar_visible = False
        self._app.layout.focus(self._body_window)
        self._reflow_for_sidebar()

    def _reflow_for_sidebar(self) -> None:
        """Render the page at the width the sidebar leaves it.

        Only beside the page does the sidebar change that width. Unlike a
        resize, the position is kept by heading: the last heading at or
        above the top line stays at the same distance from the top. The
        search runs again on the new rendering; the history and the focused
        link are dropped as on a resize, because they hold positions of the
        old one.
        """
        body_width = self._body_width()
        if body_width == self._last_body_width:
            return
        if self._resize_task is not None:
            self._resize_task.cancel()
            self._resize_task = None

        top = self._body_window.vertical_scroll
        heading: Optional[str] = None
        heading_line = 0
        for anchor, line in self._anchor_to_line.items():
            if line > top:
                break
            heading, heading_line = anchor, line

        self._render_at_width(body_width)

        new_line = self._anchor_to_line.get(heading, heading_line) if heading is not None else 0
        self._body_window.vertical_scroll = min(new_line + top - heading_line, self._plain.count("\n"))
        self._current_link = -1
        self._back_stack = []
        self._forward_stack = []
        self._matches = self._find_matches(self._search_query)
        self._current_match = min(max(self._current_match, 0), len(self._matches) - 1)

    def _select_entry_at_top(self) -> None:
        """Select the listed entry of the last heading at or above the top line of the page."""
        top = self._body_window.vertical_scroll
        self._selected = 0 if self._listed else -1
        for row, index in enumerate(self._listed):
            line = self._anchor_to_line.get(self._outline[index].anchor)
            if line is None:
                continue
            if line > top:
                break
            self._selected = row
        self._scroll_selection_into_view()

    def _apply_filter(self) -> None:
        """List the entries that match the filter text, as the patterns of
        `robotcode doc keywords` match: contains, `*` and `?`, case, spaces
        and underscores ignored.

        A level-2 entry stays listed while it or one of its level-3 entries
        matches. The selection moves to the first entry that matches itself,
        so it skips a level-2 entry that is only listed for its entries.
        """
        matcher = MultiMatcher([f"*{self._filter_buffer.text}*"], ignore="_")
        matches = [matcher.match(entry.title) for entry in self._outline]
        self._listed = []
        for index, entry in enumerate(self._outline):
            if entry.level == 2:
                end = next(
                    (i for i in range(index + 1, len(self._outline)) if self._outline[i].level == 2),
                    len(self._outline),
                )
                listed = any(matches[index:end])
            else:
                listed = matches[index]
            if listed:
                self._listed.append(index)
        self._selected = next((row for row, index in enumerate(self._listed) if matches[index]), -1)
        self._outline_window.vertical_scroll = 0
        self._scroll_selection_into_view()

    def _jump_to_selected(self) -> None:
        """Jump to the heading of the selected entry. Beside the page the
        sidebar stays and the page gets the focus; over it the sidebar closes."""
        if self._selected < 0:
            return
        self._jump_to_anchor(self._outline[self._listed[self._selected]].anchor)
        if self._sidebar_beside(self._app.output.get_size().columns):
            self._app.layout.focus(self._body_window)
        else:
            self._hide_sidebar()

    def _compute_outline_fragments(self) -> StyleAndTextTuples:
        """The listed entries, one per line, level-3 entries indented."""
        if not self._listed:
            return [("class:doc.sidebar.empty", " no matches")]
        width = _SIDEBAR_WIDTH - 1
        result: StyleAndTextTuples = []
        for row, index in enumerate(self._listed):
            entry = self._outline[index]
            if row == self._selected:
                style = "class:doc.sidebar.selected"
            elif entry.level == 2:
                style = "class:doc.sidebar.section"
            else:
                style = ""
            if row:
                result.append(("", "\n"))
            text = _fit(" " + "  " * (entry.level - 2) + entry.title, width)
            result.append((style, text, self._make_outline_click_handler(row)))
        return result

    def _make_outline_click_handler(self, row: int) -> Callable[[MouseEvent], object]:
        """A click on an entry jumps like `Enter`. Other mouse events fall
        through, so the wheel scrolls the list without changing the selection."""

        def handler(event: MouseEvent) -> object:
            if event.event_type != MouseEventType.MOUSE_UP:
                return NotImplemented
            self._selected = row
            self._jump_to_selected()
            return None

        return handler

    def _move_selection(self, delta: int) -> None:
        """Move the selection by ``delta`` rows, within the listed entries."""
        if self._listed:
            self._selected = min(max(self._selected + delta, 0), len(self._listed) - 1)
            self._scroll_selection_into_view()

    def _scroll_selection_into_view(self) -> None:
        """Scroll the list just enough to show the selected row."""
        if self._selected < 0:
            return
        info = self._outline_window.render_info
        # Before the sidebar's first render: the terminal's rows less the
        # frame, the footer, the filter field and the line below it.
        height = info.window_height if info is not None else max(1, self._app.output.get_size().rows - 5)
        top = self._outline_window.vertical_scroll
        if self._selected < top:
            self._outline_window.vertical_scroll = self._selected
        elif self._selected >= top + height:
            self._outline_window.vertical_scroll = self._selected - height + 1

    # ------------------------------------------------------------------
    # Body content + footer text — called on each render.
    # ------------------------------------------------------------------

    def _compute_body_fragments(self) -> StyleAndTextTuples:
        """Return body fragments with focus + search highlights overlaid.

        Called by `FormattedTextControl` on every render — once per
        keypress, since each scroll binding calls `app.invalidate()`.
        Piggybacks the render to detect terminal-width changes
        (`_check_resize`) so a resize schedules a debounced reflow
        instead of leaving the body at the old width.

        Short-circuit the common case (no search, no focused link)
        to avoid walking thousands of fragments + producing a list
        copy each time: `prompt_toolkit` doesn't mutate the returned
        list, so handing back our cached `_fragments` directly is safe.

        When both a link is focused and a search is active, the
        match overlay is applied last so its `reverse bold` style
        on the current match wins over the same style on the
        focused link — keeping search the more visually prominent
        navigation mode while it's in use.
        """
        self._check_resize()
        has_focused_link = self._current_link >= 0 and self._links
        if not self._matches and not has_focused_link:
            return self._fragments

        fragments = self._fragments
        if has_focused_link:
            start, end, _target = self._links[self._current_link]
            fragments = _overlay_match_highlight(fragments, [(start, end)], 0)
        if self._matches:
            fragments = _overlay_match_highlight(fragments, self._matches, self._current_match)
        return fragments

    def _compute_footer_text(self) -> StyleAndTextTuples:
        """Footer content depends on what's active:

        - sidebar focused → the sidebar's keys
        - link focused → show the focused target so the user knows
          where ``f`` will take them
        - search with matches → show the query + match counter
        - search with no matches → friendly "no matches" line
        - none of the above → the default key hints, with ``s`` on a
          document with a sidebar

        While the sidebar stands beside the page, the hints say that
        ``Esc`` hides it before it closes the viewer.
        """
        if self._sidebar_has_focus():
            return [("class:doc.footer", _SIDEBAR_HINTS)]
        if self._current_link >= 0 and self._links:
            _start, _end, target = self._links[self._current_link]
            return [
                ("class:doc.footer", "  Link "),
                ("class:doc.footer.count", f"{self._current_link + 1}/{len(self._links)}"),
                ("class:doc.footer", "  →  "),
                ("class:doc.footer.count", target),
                (
                    "class:doc.footer",
                    f"  ·  f/Enter/click: follow  ·  Tab/Shift-Tab: next/prev  ·  {self._close_hint()} ",
                ),
            ]
        if self._search_query and self._matches:
            return [
                ("class:doc.footer", " /"),
                ("class:doc.footer", self._search_query),
                ("class:doc.footer", "  "),
                ("class:doc.footer.count", f"[{self._current_match + 1}/{len(self._matches)}]"),
                ("class:doc.footer", f"  ·  n/N: next/prev  ·  /: new search  ·  {self._close_hint()} "),
            ]
        if self._search_query:
            return [
                ("class:doc.footer.nomatch", f" /{self._search_query} — no matches "),
                ("class:doc.footer", f" ·  /: search  ·  {self._close_hint()} "),
            ]
        if self._sidebar_visible:
            return [("class:doc.footer", _SIDEBAR_SHOWN_HELP_HINTS)]
        return [("class:doc.footer", _OUTLINE_HELP_HINTS if self._outline else _HELP_HINTS)]

    def _close_hint(self) -> str:
        return "Esc: hide sidebar  ·  q: close" if self._sidebar_visible else "q/Esc: close"

    # ------------------------------------------------------------------
    # Search execution + navigation.
    # ------------------------------------------------------------------

    def _on_search_accept(self, buf: Buffer) -> bool:
        """`Buffer.accept_handler` callback — fired when the user
        presses Enter in the search field. Returns `False` so
        prompt_toolkit *keeps* the buffer's content (handy if the user
        wants to refine the query)."""
        self._execute_search(buf.text)
        return False

    def _execute_search(self, query: str) -> None:
        self._search_query = query
        self._matches = self._find_matches(query)
        self._current_match = 0 if self._matches else -1
        if self._matches:
            self._scroll_to_current_match()
        self._in_search_mode = False
        self._app.layout.focus(self._body_window)

    def _find_matches(self, query: str) -> List[Tuple[int, int]]:
        """Case-insensitive substring search across the whole plain
        body. Empty queries match nothing; overlapping searches stay
        non-overlapping (advance by at least one char) to avoid an
        infinite loop on zero-width hits."""
        if not query:
            return []
        q = query.lower()
        p = self._plain.lower()
        result: List[Tuple[int, int]] = []
        pos = 0
        while True:
            idx = p.find(q, pos)
            if idx == -1:
                break
            result.append((idx, idx + len(query)))
            pos = idx + max(1, len(query))
        return result

    def _scroll_to_current_match(self) -> None:
        if not self._matches or self._current_match < 0:
            return
        start, _end = self._matches[self._current_match]
        # Line number of the match start within the plain text.
        line_no = self._plain.count("\n", 0, start)
        # Show the match a couple lines from the top for context.
        target = max(0, line_no - 1)
        max_scroll = self._max_scroll()
        self._body_window.vertical_scroll = min(target, max_scroll) if max_scroll else target

    # ------------------------------------------------------------------
    # Link navigation.
    # ------------------------------------------------------------------

    def _is_link_in_view(self, idx: int) -> bool:
        """Whether link ``idx`` falls inside the current viewport.

        Returns False for an invalid index (e.g. -1 = no focused
        link) or before the first render (no `render_info` to read
        the window height from — callers treat that as "not in
        view" so Tab snaps focus to the nearest link rather than
        cycling blindly).
        """
        if not (0 <= idx < len(self._link_lines)):
            return False
        info = self._body_window.render_info
        if info is None:
            return False
        top = self._body_window.vertical_scroll
        return top <= self._link_lines[idx] < top + info.window_height

    def _scroll_link_into_view(self, idx: int) -> None:
        """Scroll only if link ``idx`` isn't already visible.

        Pressing Tab after scrolling shouldn't yank the viewport
        back to a link the user already moved past — we leave the
        scroll alone when the focused link is in the visible area.
        Off-screen links get scrolled to "one row above the top",
        matching the search-jump rule.
        """
        if not (0 <= idx < len(self._link_lines)):
            return
        if self._is_link_in_view(idx):
            return
        target = max(0, self._link_lines[idx] - 1)
        max_scroll = self._max_scroll()
        self._body_window.vertical_scroll = min(target, max_scroll) if max_scroll else target

    def _make_link_click_handler(self, idx: int) -> Callable[[MouseEvent], object]:
        """Build a per-link mouse handler that focuses + follows on click-release.

        Returning ``NotImplemented`` for non-click events lets
        prompt_toolkit fall back to its default mouse behaviour
        (wheel scrolling on the Window). MOUSE_UP is the click-release
        event — using MOUSE_DOWN would fire mid-drag and steal
        Shift+drag text-selection attempts.
        """

        def handler(event: MouseEvent) -> object:
            if event.event_type != MouseEventType.MOUSE_UP:
                return NotImplemented
            self._current_link = idx
            self._follow_current_link()
            return None

        return handler

    def _follow_current_link(self) -> None:
        """Activate the focused link.

        For `#anchor` targets, jump to the matching section header
        within the doc (no-op if we couldn't resolve the anchor —
        rare edge case where the header text in the rendered output
        didn't match the markdown source title). For `http(s)://`
        targets, hand off to the OS's default browser via
        `webbrowser.open` — caught so an SSH session or headless
        environment can't take the viewer down. Any other target is
        handed to `link_resolver` (if configured); when it returns
        content, that document is loaded in place.

        Anchor jumps and content follows push the current position onto
        the back stack so `[` returns to it (browser-style). The forward
        stack is cleared because the new jump branches the history.
        External URL follows don't push — the viewer didn't move.
        """
        if self._current_link < 0 or not self._links:
            return
        _start, _end, target = self._links[self._current_link]
        if target.startswith("#"):
            self._jump_to_anchor(target[1:])
        elif target.startswith(("http://", "https://")):
            try:
                webbrowser.open(target)
            except Exception:
                pass
        elif self._link_resolver is not None:
            resolved = self._link_resolver(target)
            if resolved is not None:
                self._back_stack.append(self._current_state())
                self._forward_stack.clear()
                self._load_document(resolved[0], resolved[1])

    def _jump_to_anchor(self, anchor: str) -> None:
        """Scroll to the heading of ``anchor`` and push the current position
        onto the back stack. No-op if the anchor has no rendered line."""
        line = self._anchor_to_line.get(anchor)
        if line is None:
            return
        self._back_stack.append(self._current_state())
        self._forward_stack.clear()
        # `_max_scroll()` returns 0 before the first render —
        # only clamp when we have real render_info, otherwise
        # the jump always snaps to line 0.
        max_scroll = self._max_scroll()
        self._body_window.vertical_scroll = min(line, max_scroll) if max_scroll else line

    def _go_back(self) -> bool:
        """Return to the previous position from the back stack.

        Returns True if there was something to restore (so the
        keybinding can decide whether to invalidate the layout).
        Symmetric with `_go_forward` — pushing the *current* state
        onto the opposite stack before popping, so back→forward
        round-trips return the user to where they were. The previous
        document is reloaded if a content follow had replaced it.
        """
        if not self._back_stack:
            return False
        self._forward_stack.append(self._current_state())
        self._restore_state(self._back_stack.pop())
        return True

    def _go_forward(self) -> bool:
        if not self._forward_stack:
            return False
        self._back_stack.append(self._current_state())
        self._restore_state(self._forward_stack.pop())
        return True

    # ------------------------------------------------------------------
    # Scrolling.
    # ------------------------------------------------------------------

    def _max_scroll(self) -> int:
        info = self._body_window.render_info
        if info is None:
            return 0
        return max(0, info.content_height - info.window_height)

    def _scroll_by(self, lines: int) -> None:
        """Adjust `vertical_scroll` directly — clamped to content bounds.

        We don't use prompt_toolkit's `scroll_one_line_up/down` helpers
        because they read/write `event.app.current_buffer`, which is
        absent for `FormattedTextControl`. Manipulating `vertical_scroll`
        works because the control's `get_cursor_position` follows it,
        so `Window`'s built-in cursor-visibility clamping leaves us alone.
        """
        target = self._body_window.vertical_scroll + lines
        self._body_window.vertical_scroll = max(0, min(target, self._max_scroll()))

    def _page_size(self) -> int:
        info = self._body_window.render_info
        # Leave one line of overlap so the reader keeps context between pages.
        return max(1, (info.window_height - 1) if info is not None else 10)

    # ------------------------------------------------------------------
    # Key bindings — main viewer + the search-input overlay.
    # ------------------------------------------------------------------

    def _build_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()
        # All viewer keys (scroll, close, search-open, n/N) are gated
        # to "the page has the focus" so they don't fire while the user
        # is typing into the search bar or the sidebar's filter field.
        on_page = Condition(lambda: not self._in_search_mode and not self._sidebar_has_focus())
        has_matches = Condition(lambda: bool(self._matches))

        @kb.add("q", filter=on_page)
        def _close(event: KeyPressEvent) -> None:
            event.app.exit()

        @kb.add("escape", eager=True, filter=on_page)
        def _escape(event: KeyPressEvent) -> None:
            # `Esc` closes what lies on top first: a sidebar shown beside
            # the page, then the viewer. (Over the page, the sidebar has
            # the focus while it is shown, and its own `Esc` hides it.)
            if self._sidebar_visible:
                self._hide_sidebar()
                event.app.invalidate()
            else:
                event.app.exit()

        @kb.add("enter", filter=on_page)
        def _enter(event: KeyPressEvent) -> None:
            # With a link focused, follow it (same as `f`). Without
            # one, close the viewer — `q` / `Esc` do the same.
            if self._current_link >= 0 and self._links:
                self._follow_current_link()
                event.app.invalidate()
            else:
                event.app.exit()

        @kb.add("j", filter=on_page)
        @kb.add("down", filter=on_page)
        def _down(event: KeyPressEvent) -> None:
            self._scroll_by(1)
            event.app.invalidate()

        @kb.add("k", filter=on_page)
        @kb.add("up", filter=on_page)
        def _up(event: KeyPressEvent) -> None:
            self._scroll_by(-1)
            event.app.invalidate()

        @kb.add("pagedown", filter=on_page)
        @kb.add("c-d", filter=on_page)
        @kb.add(" ", filter=on_page)
        def _page_down(event: KeyPressEvent) -> None:
            self._scroll_by(self._page_size())
            event.app.invalidate()

        @kb.add("pageup", filter=on_page)
        @kb.add("c-u", filter=on_page)
        @kb.add("b", filter=on_page)
        def _page_up(event: KeyPressEvent) -> None:
            self._scroll_by(-self._page_size())
            event.app.invalidate()

        @kb.add("g", filter=on_page)
        @kb.add("home", filter=on_page)
        def _to_top(event: KeyPressEvent) -> None:
            self._body_window.vertical_scroll = 0
            event.app.invalidate()

        @kb.add("G", filter=on_page)
        @kb.add("end", filter=on_page)
        def _to_bottom(event: KeyPressEvent) -> None:
            self._body_window.vertical_scroll = self._max_scroll()
            event.app.invalidate()

        @kb.add("/", filter=on_page)
        def _open_search(event: KeyPressEvent) -> None:
            self._search_buffer.reset()
            self._in_search_mode = True
            event.app.layout.focus(self._search_window)
            event.app.invalidate()

        @kb.add("n", filter=on_page & has_matches)
        def _next_match(event: KeyPressEvent) -> None:
            self._current_match = (self._current_match + 1) % len(self._matches)
            self._scroll_to_current_match()
            event.app.invalidate()

        @kb.add("N", filter=on_page & has_matches)
        def _prev_match(event: KeyPressEvent) -> None:
            self._current_match = (self._current_match - 1) % len(self._matches)
            self._scroll_to_current_match()
            event.app.invalidate()

        # ----- Link navigation --------------------------------------
        # Tab focus-cycles links, Shift-Tab cycles backward, `f`
        # follows. We deliberately don't repurpose Enter (it stays
        # bound to "close" — model the explicit-action key after vim's
        # `gf` rather than the less-style "Enter scrolls a line"
        # split). Gated on `has_links` so the bindings don't claim
        # those keys on a doc that has no links.
        has_links = Condition(lambda: bool(self._links))

        @kb.add("tab", filter=on_page & has_links)
        def _next_link(event: KeyPressEvent) -> None:
            # When the focused link is already on screen, advance to
            # the next one. When the user has scrolled away from it
            # (or never focused one yet), skip the "cycle from
            # stale index" leap that yanks the viewport back to
            # the start: snap focus to the first link at or below
            # the current viewport top instead.
            current_top = self._body_window.vertical_scroll
            if self._is_link_in_view(self._current_link):
                self._current_link = (self._current_link + 1) % len(self._links)
            else:
                self._current_link = next(
                    (i for i, line in enumerate(self._link_lines) if line >= current_top),
                    0,
                )
            self._scroll_link_into_view(self._current_link)
            event.app.invalidate()

        @kb.add("s-tab", filter=on_page & has_links)
        def _prev_link(event: KeyPressEvent) -> None:
            # Symmetric to Tab: when the focused link is on screen,
            # step backward; otherwise pick the last link at or
            # above the current viewport bottom so Shift-Tab walks
            # back through the user's currently-visible content.
            info = self._body_window.render_info
            current_top = self._body_window.vertical_scroll
            current_bottom = current_top + (info.window_height - 1 if info is not None else 0)
            if self._is_link_in_view(self._current_link):
                self._current_link = (self._current_link - 1) % len(self._links)
            else:
                self._current_link = next(
                    (i for i in range(len(self._link_lines) - 1, -1, -1) if self._link_lines[i] <= current_bottom),
                    len(self._link_lines) - 1,
                )
            self._scroll_link_into_view(self._current_link)
            event.app.invalidate()

        @kb.add("f", filter=on_page & has_links)
        def _follow(event: KeyPressEvent) -> None:
            self._follow_current_link()
            event.app.invalidate()

        # ----- Browser-style back / forward -------------------------
        # `[` and `]` are vim-list-style navigation keys and aren't
        # claimed by anything else in the viewer. Gated on having
        # *something* to restore so the keys stay neutral on docs
        # the user hasn't navigated within yet.
        has_back = Condition(lambda: bool(self._back_stack))
        has_forward = Condition(lambda: bool(self._forward_stack))

        @kb.add("[", filter=on_page & has_back)
        def _back(event: KeyPressEvent) -> None:
            if self._go_back():
                event.app.invalidate()

        @kb.add("]", filter=on_page & has_forward)
        def _forward(event: KeyPressEvent) -> None:
            if self._go_forward():
                event.app.invalidate()

        # ----- Sidebar ----------------------------------------------
        # `s` shows the sidebar, or moves the focus to a shown one. Only
        # documents loaded with `outline=True` have one.
        has_outline = Condition(lambda: bool(self._outline))

        @kb.add("s", filter=on_page & has_outline)
        def _sidebar(event: KeyPressEvent) -> None:
            self._show_sidebar()
            event.app.invalidate()

        return kb

    def _build_search_bindings(self) -> KeyBindings:
        """Bindings attached to the search input's `BufferControl` —
        active only when the search field has focus."""
        kb = KeyBindings()

        @kb.add("escape", eager=True)
        def _cancel_search(event: KeyPressEvent) -> None:
            self._in_search_mode = False
            event.app.layout.focus(self._body_window)
            event.app.invalidate()

        return kb

    def _build_sidebar_bindings(self) -> KeyBindings:
        """Bindings attached to the sidebar's filter field — active only
        when it has the focus. Every other key is filter text."""
        kb = KeyBindings()

        @kb.add("up")
        def _previous_entry(event: KeyPressEvent) -> None:
            self._move_selection(-1)

        @kb.add("down")
        def _next_entry(event: KeyPressEvent) -> None:
            self._move_selection(1)

        @kb.add("enter")
        def _jump(event: KeyPressEvent) -> None:
            self._jump_to_selected()
            event.app.invalidate()

        @kb.add("escape", eager=True)
        def _hide(event: KeyPressEvent) -> None:
            self._hide_sidebar()
            event.app.invalidate()

        return kb
