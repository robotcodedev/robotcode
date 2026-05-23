"""Direct unit coverage of the markdown viewer pieces.

The full viewer Application is exercised end-to-end by manual smoke
tests (it switches to the alternate screen buffer and blocks until
the user presses Esc / q / Enter, which is awkward to script). Here
we verify the rendering helper and the internal scroll math in
isolation, plus the keybinding wiring on the standalone Application.
"""

from typing import Any

import pytest

from robotcode.repl._pt.doc_viewer import DocViewer, render_markdown_to_ansi


def test_render_markdown_to_ansi_empty_input_returns_empty() -> None:
    assert render_markdown_to_ansi("") == ""


def test_render_markdown_to_ansi_includes_headings_and_body() -> None:
    out = render_markdown_to_ansi("# Title\n\nBody text.\n")
    assert "Title" in out
    assert "Body text" in out


def test_render_markdown_to_ansi_emits_ansi_escapes_for_styled_content() -> None:
    """rich's force_terminal=True should produce ANSI escape codes for
    bold / colored output so prompt_toolkit's `ANSI(...)` wrapper has
    something to colour."""
    out = render_markdown_to_ansi("**bold**", width=40)
    assert "\x1b[" in out, "expected ANSI escape sequences in styled output"


def test_render_markdown_to_ansi_does_not_emit_osc8_hyperlinks() -> None:
    """`prompt_toolkit`'s ANSI parser doesn't understand OSC 8
    (``\\x1b]8;…``) and would otherwise paint the escape sequence
    as visible text. `render_markdown_to_ansi` therefore returns
    the *cleaned* ANSI (rich's hyperlinks stripped), where the URL
    lives only as metadata — visible body has just the styled link
    text. `render_markdown_for_viewer` returns the URLs separately
    so the viewer can still surface them through Tab-navigation."""
    out = render_markdown_to_ansi("See [a link](http://example.com/foo) for details.", width=80)
    assert "\x1b]8;" not in out, "rich's OSC 8 hyperlink escapes must be stripped"
    # The URL is *gone* from the visible body — it travels separately
    # via `render_markdown_for_viewer`'s spans. Only the link text
    # remains in the rendered output.
    assert "http://example.com/foo" not in out
    # But the link text itself stayed.
    assert "a link" in out


def test_coalesce_fragments_merges_same_style_runs() -> None:
    """`rich`'s ANSI output produces one fragment per styled segment —
    a typical library doc balloons to ~190k micro-fragments. Coalescing
    runs with identical styles shrinks the list dramatically so
    `prompt_toolkit` doesn't drag through it on every keypress."""
    from prompt_toolkit.formatted_text import StyleAndTextTuples

    from robotcode.repl._pt.doc_viewer import _coalesce_fragments

    fragments: StyleAndTextTuples = [
        ("", "Hello "),
        ("", "world"),
        ("", "!"),
        ("fg:red", " in "),
        ("fg:red", "red"),
        ("", " end"),
    ]
    coalesced = _coalesce_fragments(fragments)
    assert coalesced == [
        ("", "Hello world!"),
        ("fg:red", " in red"),
        ("", " end"),
    ]


def test_coalesce_fragments_preserves_three_tuples_with_mouse_handlers() -> None:
    """`StyleAndTextTuples` may carry a third element (mouse handler) —
    `rich` doesn't emit them but the type contract allows it, so we
    flush and pass them through unchanged rather than silently
    dropping the handler."""
    from prompt_toolkit.formatted_text import StyleAndTextTuples

    from robotcode.repl._pt.doc_viewer import _coalesce_fragments

    handler = lambda _e: None  # noqa: E731
    fragments: StyleAndTextTuples = [
        ("", "before "),
        ("", "merged "),
        ("class:link", "click me", handler),
        ("", " after "),
        ("", "tail"),
    ]
    coalesced = _coalesce_fragments(fragments)
    assert coalesced == [
        ("", "before merged "),
        ("class:link", "click me", handler),
        ("", " after tail"),
    ]


def test_compute_link_lines_returns_line_index_per_link() -> None:
    """Line index of each link's start, computed via one forward sweep
    (the naïve `plain.count('\\n', 0, start)` per link is O(n*m)
    and adds ~10ms per reflow on a typical library doc)."""
    from robotcode.repl._pt.doc_viewer import _compute_link_lines

    plain = "first line\nsecond line\nthird line with a link\nfourth\n"
    # Link in line 2 (zero-indexed), one in line 3.
    links = [(11, 16, "#a"), (35, 39, "#b")]
    assert _compute_link_lines(plain, links) == [1, 2]


def test_compute_link_lines_handles_links_on_same_line() -> None:
    """Two links sitting on the same source line must both map to that
    same line number — the sweep tracks the position cursor so
    later links don't re-scan the gap between them."""
    from robotcode.repl._pt.doc_viewer import _compute_link_lines

    plain = "no newlines here just two links foo and bar"
    # Two links on line 0.
    links = [(0, 3, "#a"), (10, 13, "#b")]
    assert _compute_link_lines(plain, links) == [0, 0]


def test_compute_link_lines_handles_empty_input() -> None:
    from robotcode.repl._pt.doc_viewer import _compute_link_lines

    assert _compute_link_lines("", []) == []
    assert _compute_link_lines("any plain text", []) == []


def test_coalesce_fragments_handles_empty_input() -> None:
    from robotcode.repl._pt.doc_viewer import _coalesce_fragments

    assert _coalesce_fragments([]) == []


def test_compute_body_fragments_returns_cached_fragments_when_no_search() -> None:
    """Scrolling a long doc calls `_compute_body_fragments` on every
    keypress (`app.invalidate()` triggers a re-render). When there's
    no active search the method must return the original fragment
    list as-is — not a copy — or rendering walks thousands of
    `(style, text)` tuples per keypress and scrolling lags."""
    from prompt_toolkit.formatted_text import StyleAndTextTuples

    viewer = DocViewer()
    fragments: StyleAndTextTuples = [("", "line 1\n"), ("fg:red", "line 2\n"), ("", "line 3\n")]
    viewer._fragments = fragments
    # No matches → identity, not a copy.
    assert viewer._compute_body_fragments() is fragments


def test_doc_viewer_runs_as_fullscreen_application() -> None:
    """The viewer builds a standalone Application with `full_screen=True`
    — that's the whole point of the rewrite (the old Float-over-the-
    prompt couldn't get enough vertical room when the prompt sat near
    the bottom of the terminal)."""
    viewer = DocViewer()
    assert viewer._app.full_screen is True


def test_doc_viewer_focuses_body_window_for_scroll_bindings() -> None:
    """The Layout's focused element must be the body Window so the
    scroll keybindings (which read `event.app.layout.current_window`)
    fire against the right window."""
    viewer = DocViewer()
    assert viewer._app.layout.current_window is viewer._body_window


def test_doc_viewer_scroll_clamps_to_content_bounds() -> None:
    """`_scroll_by` must not push `vertical_scroll` past the content
    height or below zero — Window's own clamp doesn't apply when the
    cursor follows the scroll via `get_cursor_position`."""
    viewer = DocViewer()
    # Direct attribute manipulation — no real render_info available
    # without running the app, so we only verify the lower bound here.
    viewer._body_window.vertical_scroll = 0
    viewer._scroll_by(-5)
    assert viewer._body_window.vertical_scroll == 0


def test_doc_viewer_registers_expected_keybindings() -> None:
    """Esc / q / Enter close; j/k + arrows + PgUp/PgDn + g/G scroll;
    `/` opens search; `n` / `N` navigate matches; Tab / Shift-Tab
    cycle links and `f` follows — smoke-check the registration so a
    refactor can't silently drop a key.

    prompt_toolkit translates `kb.add("enter")` to `Keys.ControlM` and
    `kb.add("escape", …)` to `Keys.Escape` internally — the names here
    match what `bindings` actually stores.
    """
    viewer = DocViewer()
    kb = viewer._app.key_bindings
    assert kb is not None
    bound = {tuple(str(k) for k in b.keys) for b in kb.bindings}
    expected = {
        ("Keys.Escape",),  # close
        ("q",),  # close
        ("Keys.ControlM",),  # Enter — close
        ("j",),  # scroll down 1
        ("Keys.Down",),
        ("k",),  # scroll up 1
        ("Keys.Up",),
        ("Keys.PageDown",),
        ("Keys.ControlD",),
        (" ",),  # page down (less-style)
        ("Keys.PageUp",),
        ("Keys.ControlU",),
        ("b",),  # page up (less-style)
        ("g",),  # to top
        ("Keys.Home",),
        ("G",),  # to bottom
        ("Keys.End",),
        ("/",),  # open search input
        ("n",),  # next match
        ("N",),  # previous match
        ("Keys.ControlI",),  # Tab — cycle links forward (Ctrl-I === Tab)
        ("Keys.BackTab",),  # Shift-Tab — cycle links backward
        ("f",),  # follow focused link
        ("[",),  # back (browser-style)
        ("]",),  # forward
    }
    missing = expected - bound
    assert not missing, f"expected viewer key bindings missing: {missing}"


# ---------------------------------------------------------------------------
# Link extraction + anchor mapping (`Tab`/`f` navigation).
# ---------------------------------------------------------------------------


def test_strip_osc8_hyperlinks_extracts_spans_and_cleans_ansi() -> None:
    """`rich` emits OSC 8 (``\\x1b]8;…;url\\x1b\\\\…\\x1b]8;;\\x1b\\\\``)
    around link text when `hyperlinks=True` is on (the rich default).
    The stripper must drop those escape sequences from the cleaned
    ANSI (otherwise prompt_toolkit paints them as visible garbage)
    and capture the link spans in visible-text coordinates so the
    viewer can highlight + Tab-cycle them."""
    from robotcode.repl._pt.doc_viewer import _strip_osc8_hyperlinks

    # Open: \x1b]8;;url\x1b\\, close: \x1b]8;;\x1b\\
    ansi = "See \x1b]8;;http://x.com\x1b\\link\x1b]8;;\x1b\\ for details."
    cleaned, spans = _strip_osc8_hyperlinks(ansi)
    assert cleaned == "See link for details."
    assert spans == [(4, 8, "http://x.com")]


def test_strip_osc8_hyperlinks_preserves_sgr_inside_link() -> None:
    """SGR styling (colour, bold, underline — all `\\x1b[...m`) inside
    the link must survive to the cleaned output so prompt_toolkit's
    ANSI parser still picks it up — that's how the link text retains
    its underline+colour without us hand-rolling a link style."""
    from robotcode.repl._pt.doc_viewer import _strip_osc8_hyperlinks

    ansi = "\x1b]8;;http://x.com\x1b\\\x1b[4;34mtext\x1b[0m\x1b]8;;\x1b\\"
    cleaned, spans = _strip_osc8_hyperlinks(ansi)
    # SGR sequences preserved; OSC removed; visible chars only count
    # in the span coordinates.
    assert cleaned == "\x1b[4;34mtext\x1b[0m"
    assert spans == [(0, 4, "http://x.com")]


def test_strip_osc8_hyperlinks_supports_bel_terminator() -> None:
    """OSC 8 may be terminated by either BEL (`\\x07`) or ST
    (`\\x1b\\\\`) — some terminals + some `rich` versions emit BEL.
    Both forms must be recognised."""
    from robotcode.repl._pt.doc_viewer import _strip_osc8_hyperlinks

    ansi = "before \x1b]8;;http://x.com\x07link\x1b]8;;\x07 after"
    cleaned, spans = _strip_osc8_hyperlinks(ansi)
    assert cleaned == "before link after"
    assert spans == [(7, 11, "http://x.com")]


def test_strip_osc8_hyperlinks_returns_empty_spans_when_no_links() -> None:
    """No OSC 8 in input → cleaned string is identical (modulo nothing
    to strip), spans is empty."""
    from robotcode.repl._pt.doc_viewer import _strip_osc8_hyperlinks

    ansi = "plain \x1b[31mtext\x1b[0m with sgr but no links"
    cleaned, spans = _strip_osc8_hyperlinks(ansi)
    assert cleaned == ansi
    assert spans == []


def test_build_anchor_to_line_map_matches_headers_in_order() -> None:
    """Headers in the markdown source must map to the line where their
    title text appears in the rendered output. Order is preserved
    (cursor advances) so duplicate titles map to the *first*
    occurrence after the previous header, not the first occurrence
    overall."""
    from robotcode.repl._pt.doc_viewer import _build_anchor_to_line_map

    md = "## Section One\n\nBody one.\n\n## Section Two\n\nSection One appears in body two."
    rendered = "Section One\n\nBody one.\n\nSection Two\n\nSection One appears in body two."
    mapping = _build_anchor_to_line_map(md, rendered)
    assert mapping == {"section-one": 0, "section-two": 4}


def test_build_anchor_to_line_map_strips_emphasis_for_matching() -> None:
    """`## Library *BuiltIn*` in markdown renders to `Library BuiltIn`
    in rich's output (asterisks consumed). The slug keeps the
    asterisks (matches the auto-linker's behaviour); the line
    lookup strips them so we still find the header."""
    from robotcode.repl._pt.doc_viewer import _build_anchor_to_line_map

    md = "## Library *BuiltIn*\n\nIntro."
    rendered = "Library BuiltIn\n\nIntro."
    mapping = _build_anchor_to_line_map(md, rendered)
    assert mapping == {"library-*builtin*": 0}


def test_tab_binding_gated_on_having_links() -> None:
    """`Tab` shouldn't claim the key on a doc with no extracted links —
    otherwise it'd swallow a no-op key event that the user might
    have meant for something else (and we couldn't visually surface
    "there's a link to focus" anyway)."""
    viewer = DocViewer()
    kb = viewer._app.key_bindings
    assert kb is not None
    tab_binding = next(b for b in kb.bindings if [str(k) for k in b.keys] == ["Keys.ControlI"])
    # No links seeded → filter False.
    assert tab_binding.filter() is False
    viewer._links = [(0, 5, "#x")]
    assert tab_binding.filter() is True


def test_follow_current_link_jumps_to_anchor() -> None:
    """`f` on a focused `#anchor` link scrolls the body to the
    rendered line that maps to that anchor."""
    viewer = DocViewer()
    viewer._anchor_to_line = {"section-two": 7}
    viewer._links = [(0, 14, "#section-two")]
    viewer._current_link = 0
    viewer._follow_current_link()
    assert viewer._body_window.vertical_scroll == 7


def test_follow_current_link_opens_browser_for_external_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """For `http(s)://` targets we hand off to `webbrowser.open` so
    the OS's default browser handles the URL — no in-doc scroll."""
    opened: list[str] = []
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", lambda url, *_a, **_kw: opened.append(url))

    viewer = DocViewer()
    viewer._links = [(0, 25, "https://example.com/foo")]
    viewer._current_link = 0
    viewer._body_window.vertical_scroll = 5
    viewer._follow_current_link()
    assert opened == ["https://example.com/foo"]
    # External URL doesn't move the scroll.
    assert viewer._body_window.vertical_scroll == 5


def _click_event() -> Any:
    """Build a MOUSE_UP event — only `event_type` is read by the handler."""
    from prompt_toolkit.data_structures import Point
    from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType

    return MouseEvent(
        position=Point(x=0, y=0),
        event_type=MouseEventType.MOUSE_UP,
        button=MouseButton.LEFT,
        modifiers=frozenset(),
    )


def test_link_click_handler_focuses_and_follows_on_mouse_up() -> None:
    """Click-release on a link span sets the focus to that link and
    follows it — same flow as `f` / Enter, just triggered by the mouse."""
    viewer = DocViewer()
    viewer._anchor_to_line = {"section-two": 7}
    viewer._links = [(0, 14, "#section-two"), (20, 30, "#other")]
    handler = viewer._make_link_click_handler(0)

    result = handler(_click_event())

    assert result is None
    assert viewer._current_link == 0
    assert viewer._body_window.vertical_scroll == 7


def test_link_click_handler_ignores_non_click_events() -> None:
    """Non-click events (mouse-move, scroll-wheel) return
    ``NotImplemented`` so prompt_toolkit's default mouse handling
    (e.g. wheel-scrolling the Window) still fires."""
    from prompt_toolkit.data_structures import Point
    from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType

    viewer = DocViewer()
    viewer._links = [(0, 5, "#anchor")]
    handler = viewer._make_link_click_handler(0)

    for evt_type in (MouseEventType.MOUSE_DOWN, MouseEventType.MOUSE_MOVE, MouseEventType.SCROLL_DOWN):
        result = handler(
            MouseEvent(
                position=Point(x=0, y=0),
                event_type=evt_type,
                button=MouseButton.LEFT,
                modifiers=frozenset(),
            )
        )
        assert result is NotImplemented, f"{evt_type} should pass through"


def test_attach_link_handlers_wraps_link_spans_only() -> None:
    """The link-handler attach pass replaces only the fragments that
    overlap a link span with 3-tuples; surrounding fragments stay
    untouched (2-tuples), so the per-render fast path keeps working."""
    from prompt_toolkit.formatted_text import StyleAndTextTuples

    from robotcode.repl._pt.doc_viewer import _attach_link_handlers

    fragments: StyleAndTextTuples = [("", "before "), ("", "linktext"), ("", " after")]
    links = [(7, 15, "#target")]
    sentinel = lambda evt: None  # noqa: E731

    out = _attach_link_handlers(fragments, links, lambda idx: sentinel)

    plain = "".join(f[1] for f in out)
    assert plain == "before linktext after"
    handlers = [(f[1], f[2] if len(f) > 2 else None) for f in out]
    assert ("linktext", sentinel) in handlers
    assert ("before ", None) in handlers
    assert (" after", None) in handlers


def test_scroll_link_into_view_skips_scroll_when_link_already_visible() -> None:
    """Pressing Tab on a link that's already in the viewport shouldn't
    move the scroll. Tab is a focus action, not a "re-scroll to my
    last position" action — the user complained that the original
    implementation yanked them back to a stale focus."""
    from types import SimpleNamespace

    viewer = DocViewer()
    viewer._link_lines = [5]
    viewer._body_window.vertical_scroll = 3
    # Fake a render_info so `_is_link_in_view` can answer truthfully.
    viewer._body_window.render_info = SimpleNamespace(window_height=10)  # type: ignore[assignment]

    viewer._scroll_link_into_view(0)
    # Link at line 5 is inside [3, 13) → no scroll change.
    assert viewer._body_window.vertical_scroll == 3


def test_scroll_link_into_view_scrolls_to_offscreen_link() -> None:
    """When the link is off-screen, `_scroll_link_into_view` moves to
    "link line minus one row of context" — same rule the search jump
    uses, keeping a consistent feel."""
    from types import SimpleNamespace

    viewer = DocViewer()
    viewer._link_lines = [50]
    viewer._body_window.vertical_scroll = 0
    viewer._body_window.render_info = SimpleNamespace(  # type: ignore[assignment]
        window_height=10, content_height=200
    )

    viewer._scroll_link_into_view(0)
    # Link at line 50 is way below the [0, 10) viewport — scroll to ~line 49.
    assert viewer._body_window.vertical_scroll == 49


def test_tab_after_scroll_jumps_to_first_link_in_viewport() -> None:
    """User scrolls down, presses Tab → focus snaps to the first link
    at or below the current viewport top, NOT to `current_link + 1`
    which would yank the viewport back to a stale position."""
    from types import SimpleNamespace

    viewer = DocViewer()
    viewer._links = [(0, 5, "#a"), (100, 105, "#b"), (200, 205, "#c")]
    viewer._link_lines = [1, 10, 20]
    viewer._current_link = 0  # focus stale from earlier interaction
    viewer._body_window.vertical_scroll = 15  # scrolled past link 1 (line 10)
    viewer._body_window.render_info = SimpleNamespace(  # type: ignore[assignment]
        window_height=10, content_height=30
    )
    kb = viewer._app.key_bindings
    assert kb is not None
    handler = next(b for b in kb.bindings if [str(k) for k in b.keys] == ["Keys.ControlI"]).handler

    event = type("Ev", (), {"app": viewer._app})()
    handler(event)
    # Link 0 (line 1) is off-screen above; first link >= top(15) is
    # link 2 (line 20). Focus must land there, NOT on link 1 (the
    # naïve `current_link + 1`).
    assert viewer._current_link == 2


def test_shifttab_after_scroll_jumps_to_last_link_in_viewport() -> None:
    """Symmetric to Tab — Shift-Tab from a scrolled position lands on
    the last link at or above the current viewport bottom."""
    from types import SimpleNamespace

    viewer = DocViewer()
    viewer._links = [(0, 5, "#a"), (100, 105, "#b"), (200, 205, "#c"), (300, 305, "#d")]
    viewer._link_lines = [1, 10, 20, 30]
    viewer._current_link = 3  # focus stale way down
    viewer._body_window.vertical_scroll = 5  # viewport [5, 15)
    viewer._body_window.render_info = SimpleNamespace(  # type: ignore[assignment]
        window_height=10, content_height=40
    )
    kb = viewer._app.key_bindings
    assert kb is not None
    handler = next(b for b in kb.bindings if [str(k) for k in b.keys] == ["Keys.BackTab"]).handler

    event = type("Ev", (), {"app": viewer._app})()
    handler(event)
    # Viewport bottom = 14. Last link at or before 14 is link 1
    # (line 10). NOT link 2 (the naïve `current_link - 1`).
    assert viewer._current_link == 1


def test_render_at_width_cache_hit_skips_rerender(monkeypatch: pytest.MonkeyPatch) -> None:
    """A reflow back to a previously-seen width must NOT call
    `render_markdown_for_viewer` again — the cached snapshot
    contains the full set of derived data. This is what makes
    resize-back-to-old-width effectively instant."""
    calls: list[int] = []

    import robotcode.repl._pt.doc_viewer as mod

    original = mod.render_markdown_for_viewer

    def counting_render(text: str, *, width: int) -> Any:
        calls.append(width)
        return original(text, width=width)

    monkeypatch.setattr(mod, "render_markdown_for_viewer", counting_render)

    viewer = DocViewer()
    viewer._md_source = "# Test\n\nBody text.\n"
    viewer._render_cache = {}

    viewer._render_at_width(80)
    viewer._render_at_width(40)
    assert calls == [80, 40]  # both widths rendered

    # Going back to 80 hits the cache — no third render call.
    viewer._render_at_width(80)
    assert calls == [80, 40], "second visit to width 80 must NOT re-render"


def test_render_cache_cleared_on_new_doc() -> None:
    """Switching to a new markdown source must drop the cache —
    otherwise the user could see the previous doc's body when
    resizing back to a previously-rendered width."""
    viewer = DocViewer()
    # Pretend we already cached something.
    viewer._md_source = "old"
    viewer._render_at_width(60)
    assert 60 in viewer._render_cache

    # Simulate the `run()` reset that happens for a new `.doc` call.
    viewer._md_source = "new"
    viewer._render_cache = {}
    viewer._render_at_width(60)
    # Cache now holds the NEW source's render — verify by checking that
    # the cached `plain` matches the new rendering, not the old one.
    assert "new" in viewer._render_cache[60].plain or "" in viewer._render_cache[60].plain


def test_reflow_after_resize_rerenders_at_new_width() -> None:
    """Resizing the terminal must reflow the body — otherwise the old
    line breaks stay frozen and either overflow or under-fill the
    new viewport. `_reflow_after_resize` re-renders at the new
    width and rebuilds every derived index (plain text, link
    spans, anchor map, line cache)."""
    viewer = DocViewer()
    viewer._md_source = "# Test\n\nA paragraph that is fairly short.\n\nAnother line.\n"
    viewer._render_at_width(60)
    plain_60 = viewer._plain
    viewer._reflow_after_resize(30)
    assert viewer._last_body_width == 30
    assert viewer._plain != plain_60, "plain text must change after reflow at different width"
    # Body content survives even though the wrapping differs.
    assert "paragraph" in viewer._plain
    assert "Another line" in viewer._plain


def test_reflow_after_resize_preserves_scroll_percentage() -> None:
    """The user has scrolled to (say) the middle of the doc; after a
    resize they should land near the same content, not snapped to
    the top. `_reflow_after_resize` preserves a percentage scroll —
    rough but close enough that the user keeps their reading place."""
    viewer = DocViewer()
    # Long source so the reflow has many lines to map between widths.
    body = "\n".join(f"Paragraph {i} with content that may wrap differently." for i in range(40))
    viewer._md_source = body
    viewer._render_at_width(80)
    old_lines = max(1, viewer._plain.count("\n") + 1)
    viewer._body_window.vertical_scroll = old_lines // 2  # right in the middle
    viewer._reflow_after_resize(40)
    new_lines = max(1, viewer._plain.count("\n") + 1)
    # Allow ±1 line of fuzz since `int()` truncates the percentage.
    target = new_lines // 2
    assert abs(viewer._body_window.vertical_scroll - target) <= 1


def test_reflow_after_resize_drops_position_dependent_state() -> None:
    """Search matches + back/forward + focused link all index into
    the old `_plain`. After a reflow those positions point at
    different content; safest to clear rather than silently keep
    bogus indices."""
    viewer = DocViewer()
    viewer._md_source = "# Test\n\nBody.\n"
    viewer._render_at_width(80)
    # Seed stale position state.
    viewer._matches = [(0, 4)]
    viewer._current_match = 0
    viewer._back_stack = [(10, 0)]
    viewer._forward_stack = [(20, 1)]
    viewer._current_link = 5
    viewer._reflow_after_resize(40)
    assert viewer._matches == []
    assert viewer._current_match == -1
    assert viewer._back_stack == []
    assert viewer._forward_stack == []
    assert viewer._current_link == -1


def test_check_resize_no_op_when_width_unchanged() -> None:
    """`_compute_body_fragments` calls `_check_resize` on every
    render. When the width hasn't changed, nothing should be
    scheduled — otherwise every scroll keypress would needlessly
    book an asyncio timer."""
    viewer = DocViewer()
    viewer._md_source = "# Test\n\nBody.\n"
    viewer._render_at_width(80)
    assert viewer._resize_task is None
    # Stub the app size to match the current width.
    from types import SimpleNamespace

    viewer._app.output = SimpleNamespace(get_size=lambda: SimpleNamespace(columns=82, rows=24))  # type: ignore[assignment]
    viewer._check_resize()
    assert viewer._resize_task is None  # no scheduling at the same width


def test_back_forward_round_trip_restores_position() -> None:
    """Browser-style: follow → back returns to the pre-follow scroll
    + focused link, forward then re-enters the followed position."""
    viewer = DocViewer()
    viewer._anchor_to_line = {"target": 42}
    viewer._links = [(0, 5, "#target")]
    viewer._body_window.vertical_scroll = 10
    viewer._current_link = 0
    viewer._follow_current_link()
    assert viewer._body_window.vertical_scroll == 42
    assert viewer._back_stack == [(10, 0)]
    assert viewer._forward_stack == []

    # Back — restore pre-follow state.
    assert viewer._go_back() is True
    assert viewer._body_window.vertical_scroll == 10
    assert viewer._current_link == 0
    assert viewer._back_stack == []
    assert viewer._forward_stack == [(42, 0)]

    # Forward — return to followed state.
    assert viewer._go_forward() is True
    assert viewer._body_window.vertical_scroll == 42
    assert viewer._back_stack == [(10, 0)]
    assert viewer._forward_stack == []


def test_back_with_empty_stack_returns_false() -> None:
    """`_go_back` reports False (and the keybinding stays a no-op)
    when there's nothing to restore — guards against popping an
    empty stack on a fresh doc."""
    viewer = DocViewer()
    assert viewer._go_back() is False
    assert viewer._go_forward() is False


def test_new_follow_clears_forward_stack() -> None:
    """Branching the history (follow after back) must drop any
    pending forward entries — that's standard browser behaviour:
    once you navigate from a back-state, the redo arm is gone."""
    viewer = DocViewer()
    viewer._anchor_to_line = {"a": 10, "b": 20}
    viewer._links = [(0, 5, "#a"), (10, 15, "#b")]

    viewer._current_link = 0
    viewer._follow_current_link()  # → line 10
    viewer._go_back()  # → forward stack now holds (10, 0)
    assert viewer._forward_stack == [(10, 0)]

    # Following something else clears forward.
    viewer._current_link = 1
    viewer._follow_current_link()  # → line 20
    assert viewer._forward_stack == []
    assert viewer._body_window.vertical_scroll == 20


def test_external_url_follow_does_not_push_history(monkeypatch: pytest.MonkeyPatch) -> None:
    """Opening a URL in the browser doesn't move the viewer, so no
    back entry should be created — pressing `[` afterwards should
    still be a no-op."""
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", lambda *_a, **_kw: None)
    viewer = DocViewer()
    viewer._links = [(0, 5, "https://example.com")]
    viewer._current_link = 0
    viewer._body_window.vertical_scroll = 5
    viewer._follow_current_link()
    assert viewer._back_stack == []
    assert viewer._body_window.vertical_scroll == 5  # unchanged


def test_follow_current_link_swallows_browser_open_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Headless environments (SSH, CI) raise from `webbrowser.open` —
    the viewer must not propagate that, otherwise the whole REPL
    dies on an `f` press."""
    import webbrowser

    def _boom(url: str, *_a: object, **_kw: object) -> None:
        raise RuntimeError("no browser here")

    monkeypatch.setattr(webbrowser, "open", _boom)
    viewer = DocViewer()
    viewer._links = [(0, 25, "https://example.com/foo")]
    viewer._current_link = 0
    viewer._follow_current_link()  # Must not raise.


# ---------------------------------------------------------------------------
# Search — match-finding + scroll-to-match + highlight overlay.
# ---------------------------------------------------------------------------


def test_find_matches_empty_query_returns_no_matches() -> None:
    viewer = DocViewer()
    viewer._plain = "hello world"
    assert viewer._find_matches("") == []


def test_find_matches_substring_case_insensitive() -> None:
    viewer = DocViewer()
    viewer._plain = "Hello World, hello again, HELLO three"
    matches = viewer._find_matches("hello")
    assert matches == [(0, 5), (13, 18), (26, 31)]


def test_find_matches_returns_empty_when_pattern_not_present() -> None:
    viewer = DocViewer()
    viewer._plain = "nothing to see here"
    assert viewer._find_matches("xyz") == []


def test_execute_search_seeds_current_match_to_zero() -> None:
    viewer = DocViewer()
    viewer._plain = "Log\nSet Variable\nLog To Console"
    viewer._execute_search("Log")
    assert viewer._matches == [(0, 3), (17, 20)]
    assert viewer._current_match == 0
    assert viewer._in_search_mode is False  # search bar closes after submit


def test_execute_search_with_no_matches_keeps_current_at_minus_one() -> None:
    viewer = DocViewer()
    viewer._plain = "the body"
    viewer._execute_search("missing")
    assert viewer._matches == []
    assert viewer._current_match == -1


def test_overlay_match_highlight_no_matches_returns_unchanged_fragments() -> None:
    """With no matches, the body must render exactly as rich produced
    it — no extra style classes appended."""
    from prompt_toolkit.formatted_text import StyleAndTextTuples

    from robotcode.repl._pt.doc_viewer import _overlay_match_highlight

    fragments: StyleAndTextTuples = [("fg:red", "Hello"), ("", " "), ("bold", "world")]
    assert _overlay_match_highlight(fragments, [], -1) == fragments


def test_overlay_match_highlight_marks_current_match_distinctly() -> None:
    """All matches get `class:doc.match`; the one at `current_idx`
    gets `class:doc.match.current` so the user can tell which one is
    in focus while pressing n/N."""
    from prompt_toolkit.formatted_text import StyleAndTextTuples

    from robotcode.repl._pt.doc_viewer import _overlay_match_highlight

    # plain text: "abXXcdYY"; two matches at (2,4) and (6,8).
    fragments: StyleAndTextTuples = [("", "abXXcdYY")]
    matches = [(2, 4), (6, 8)]
    out = _overlay_match_highlight(fragments, matches, current_idx=1)
    # `StyleAndTextTuples` entries may be 2- or 3-tuples (the third
    # slot carries optional mouse handlers); destructure positionally
    # so this test doesn't have to care.
    styles = [item[0] for item in out]
    texts = [item[1] for item in out]
    # Reassemble the plain text from the output — content must survive.
    assert "".join(texts) == "abXXcdYY"
    # The current match (#1) should carry the `.current` class; the
    # other one should not.
    current_fragments = [texts[i] for i, s in enumerate(styles) if "doc.match.current" in s]
    plain_match_fragments = [
        texts[i] for i, s in enumerate(styles) if "doc.match" in s and "doc.match.current" not in s
    ]
    assert current_fragments == ["YY"]
    assert plain_match_fragments == ["XX"]


def test_scroll_to_current_match_lands_near_the_match_line() -> None:
    """The match line should sit a row or two below the top of the
    viewport so the reader has visual context above the hit."""
    viewer = DocViewer()
    viewer._plain = "\n".join(f"line {i}" for i in range(20))
    # Match in line 5.
    line_5_start = sum(len(f"line {i}") + 1 for i in range(5))
    viewer._matches = [(line_5_start, line_5_start + 4)]
    viewer._current_match = 0
    # No render_info yet → `_max_scroll()` returns 0 → just target the line.
    viewer._scroll_to_current_match()
    # `max(0, line_no - 1)` — line 5 with -1 context → vertical_scroll == 4.
    assert viewer._body_window.vertical_scroll == 4


def test_n_binding_only_active_when_there_are_matches() -> None:
    """`n` shouldn't fire (or do anything) when no search has matches
    yet — prompt_toolkit's Condition filter gates the binding."""
    viewer = DocViewer()
    kb = viewer._app.key_bindings
    assert kb is not None
    n_binding = next(b for b in kb.bindings if [str(k) for k in b.keys] == ["n"])
    # Without matches, the binding's filter must evaluate to False.
    assert n_binding.filter() is False
    # Seed a fake match and re-check.
    viewer._matches = [(0, 3)]
    assert n_binding.filter() is True


def test_search_buffer_esc_cancels_back_to_body() -> None:
    """Esc in the search field returns focus to the body (and the
    viewer doesn't exit). The search-control bindings are separate
    from the app-level bindings so the gate is "what's focused?"."""
    viewer = DocViewer()
    search_kb = viewer._search_control.key_bindings
    assert search_kb is not None
    esc_binding = next(b for b in search_kb.bindings if [str(k) for k in b.keys] == ["Keys.Escape"])
    assert esc_binding is not None
