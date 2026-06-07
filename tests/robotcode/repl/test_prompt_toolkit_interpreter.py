"""Tests for `PromptToolkitConsoleInterpreter` — the prompt_toolkit-driven
REPL interpreter. `ConsoleInterpreter` has its own coverage for plain mode.
"""

from pathlib import Path
from typing import Any, List

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory

from robotcode.repl._pt.components import _ReplFileHistory, _RobotCompleter
from robotcode.repl.prompt_toolkit_interpreter import PromptToolkitConsoleInterpreter


def _seed_history(path: Path, entries: list[str]) -> None:
    """Populate a history file via prompt_toolkit's own FileHistory writer
    so the on-disk format matches what the backend reads back."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    history = FileHistory(str(path))
    for entry in entries:
        history.store_string(entry)


# ---------------------------------------------------------------------------
# _RobotCompleter — bridge from candidates_for() to Completion objects.
# ---------------------------------------------------------------------------


def test_robot_completer_yields_candidates_with_correct_start_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`start_position` is signed-negative: chars before cursor to replace."""
    from robotcode.repl._pt.completion import Candidate

    # Patch in the consumer namespace (see [[feedback-mock-where-used]]).
    # Stage 6 switched the completer to `candidates_for_rich` which
    # returns `Candidate(label, detail)` objects.
    monkeypatch.setattr(
        "robotcode.repl._pt.components.candidates_for_rich",
        lambda ctx, **kwargs: [Candidate("Log", "Log a message"), Candidate("Log To Console", "Log to stdout")],
    )

    completer = _RobotCompleter()
    completions = list(completer.get_completions(Document("Lo"), CompleteEvent()))

    assert [c.text for c in completions] == ["Log", "Log To Console"]
    # Prefix "Lo" sits at column 0; tokenize gives replace_start=0,
    # so start_position is 0 - len("Lo") == -2.
    assert all(c.start_position == -2 for c in completions)


def test_robot_completer_empty_candidate_list_yields_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "robotcode.repl._pt.components.candidates_for_rich",
        lambda ctx, **kwargs: [],
    )
    completer = _RobotCompleter()
    completions = list(completer.get_completions(Document("anything"), CompleteEvent()))
    assert completions == []


def test_robot_completer_passes_detail_through_to_display_meta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`Candidate.detail` flows into `Completion.display_meta` so the
    popup shows what each candidate is (first-line doc, import kind,
    variable value, …)."""
    from robotcode.repl._pt.completion import Candidate

    monkeypatch.setattr(
        "robotcode.repl._pt.components.candidates_for_rich",
        lambda ctx, **kwargs: [Candidate("Log", "Log a message with the given level")],
    )

    completer = _RobotCompleter()
    completions = list(completer.get_completions(Document("Lo"), CompleteEvent()))

    assert len(completions) == 1
    # prompt_toolkit stores display_meta as either FormattedText or
    # a plain string — coerce to str for the assertion.
    assert "Log a message" in str(completions[0].display_meta)


# ---------------------------------------------------------------------------
# PromptToolkitConsoleInterpreter — wiring smoke tests (no real terminal involved).
# ---------------------------------------------------------------------------


def test_keyword_list_entry_emits_followable_link() -> None:
    """The `.kw` list renders each keyword as a `kw:` link with the
    space-containing qualified name percent-encoded so markdown keeps
    it as one link target."""
    interp = PromptToolkitConsoleInterpreter(app=None)
    entry = interp._keyword_list_entry("Collections", "Append To List")
    assert entry == "- [Append To List](kw:Collections.Append%20To%20List)"


def test_resolve_doc_link_decodes_kw_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Following a `kw:` link decodes the target and asks `_keyword_doc`
    for that keyword's page."""
    interp = PromptToolkitConsoleInterpreter(app=None)
    seen: List[str] = []

    def _fake_doc(name: str) -> Any:
        seen.append(name)
        return ("Append To List", "# Append To List")

    monkeypatch.setattr(interp, "_keyword_doc", _fake_doc)
    assert interp._resolve_doc_link("kw:Collections.Append%20To%20List") == ("Append To List", "# Append To List")
    assert seen == ["Collections.Append To List"]


def test_resolve_doc_link_ignores_non_kw_targets() -> None:
    interp = PromptToolkitConsoleInterpreter(app=None)
    assert interp._resolve_doc_link("#section") is None
    assert interp._resolve_doc_link("https://example.com") is None


def test_prompt_toolkit_interpreter_uses_filehistory_at_history_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The backend wires a stock `FileHistory` against the file `history_path()` returns."""
    target = tmp_path / "h"
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: target)

    interp = PromptToolkitConsoleInterpreter(app=None)
    history = interp._session.history
    assert isinstance(history, FileHistory)
    assert Path(str(history.filename)) == target


def test_prompt_toolkit_interpreter_threads_no_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`no_history=True` swaps in an InMemoryHistory — the on-disk file is left alone."""
    from prompt_toolkit.history import InMemoryHistory

    histfile = tmp_path / "h"
    _seed_history(histfile, ["ancient_line"])
    pristine = histfile.read_text()
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)

    interp = PromptToolkitConsoleInterpreter(app=None, no_history=True)
    history = interp._session.history
    assert isinstance(history, InMemoryHistory)
    history.store_string("nope")
    # File untouched — InMemoryHistory writes to memory only.
    assert histfile.read_text() == pristine


def test_prompt_toolkit_interpreter_survives_malformed_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A history file in an unrecognised format must not crash startup.
    prompt_toolkit's FileHistory uses `errors='replace'` on UTF-8 decode
    and ignores lines that don't start with `+`, so we just inherit
    that behaviour — the file appears empty to the REPL and new entries
    get appended in the proper format."""
    histfile = tmp_path / "h"
    histfile.write_bytes(b"\xff\xfe legacy junk\nfirst\nsecond\n")
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)

    interp = PromptToolkitConsoleInterpreter(app=None)
    assert interp.get_history() == []


def test_prompt_toolkit_interpreter_caps_load_to_max_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`load_history_strings` is sliced to `max_entries` so prompt_toolkit
    only sees the newest N even if the file is externally oversized."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c", "d", "e"])
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)
    monkeypatch.setenv("ROBOTCODE_REPL_HISTORY_SIZE", "3")

    interp = PromptToolkitConsoleInterpreter(app=None)
    # Newest three survive in the load, oldest → newest order.
    assert interp.get_history() == ["c", "d", "e"]


def test_prompt_toolkit_interpreter_under_cap_returns_all_entries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When the file holds fewer entries than the cap, all of them load."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b"])
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)
    monkeypatch.setenv("ROBOTCODE_REPL_HISTORY_SIZE", "10")

    interp = PromptToolkitConsoleInterpreter(app=None)
    assert interp.get_history() == ["a", "b"]


def test_prompt_toolkit_interpreter_append_evicts_oldest_when_over_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When an `append_string` would push the file past the cap, the
    oldest entry is dropped on disk. Keeps the file bounded over a long
    interactive session, not just at startup."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c"])
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)
    monkeypatch.setenv("ROBOTCODE_REPL_HISTORY_SIZE", "3")

    interp = PromptToolkitConsoleInterpreter(app=None)
    # Sanity: we start at the cap.
    assert interp.get_history() == ["a", "b", "c"]
    # Adding one more should evict "a" (oldest).
    interp._session.history.append_string("d")
    assert interp.get_history() == ["b", "c", "d"]
    # And another append evicts "b".
    interp._session.history.append_string("e")
    assert interp.get_history() == ["c", "d", "e"]


# ---------------------------------------------------------------------------
# _ReplFileHistory — direct unit coverage of the History-class contract
# ---------------------------------------------------------------------------


def test_repl_file_history_clear_returns_true_and_wipes_cache(tmp_path: Path) -> None:
    """`clear()` returns True on success and leaves the in-memory cache empty
    so prompt_toolkit's next arrow-up reflects the empty state."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b"])
    history = _ReplFileHistory(str(histfile), max_entries=10)
    # Prime the cache.
    list(history.load_history_strings())

    assert history.clear() is True
    assert list(history.load_history_strings()) == []
    assert history._loaded_strings == []


def test_repl_file_history_delete_returns_true_when_in_range(tmp_path: Path) -> None:
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c"])
    history = _ReplFileHistory(str(histfile), max_entries=10)

    assert history.delete(2) is True
    # Newest-first: c, then a (b was at idx 2 in oldest-first listing → dropped).
    assert list(history.load_history_strings()) == ["c", "a"]


def test_repl_file_history_delete_returns_false_when_out_of_range(tmp_path: Path) -> None:
    histfile = tmp_path / "h"
    _seed_history(histfile, ["only"])
    history = _ReplFileHistory(str(histfile), max_entries=10)

    assert history.delete(99) is False
    assert history.delete(0) is False
    # Original entry untouched.
    assert list(history.load_history_strings()) == ["only"]


def test_repl_file_history_append_keeps_cache_in_sync_after_eviction(tmp_path: Path) -> None:
    """When `append_string` triggers an eviction, `_loaded_strings` must
    match the on-disk state — otherwise prompt_toolkit's in-memory
    arrow-up walks a list that disagrees with the file."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c"])
    history = _ReplFileHistory(str(histfile), max_entries=3)
    # Force the cache to be populated.
    list(history.load_history_strings())
    history._loaded = True
    history._loaded_strings = ["c", "b", "a"]  # newest-first, mirrors file

    history.append_string("d")

    # File should now hold b, c, d (oldest-first); newest-first is d, c, b.
    on_disk = list(history.load_history_strings())
    assert on_disk == ["d", "c", "b"]
    assert history._loaded_strings == on_disk, "cache must match disk after eviction"


def test_repl_file_history_load_islice_caps_externally_oversized_file(tmp_path: Path) -> None:
    """If the file was externally edited and now holds more than max_entries,
    `load_history_strings` still returns at most max_entries (defense in depth)."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c", "d", "e"])
    history = _ReplFileHistory(str(histfile), max_entries=2)

    # Newest-first, capped to 2.
    assert list(history.load_history_strings()) == ["e", "d"]


# ---------------------------------------------------------------------------
# _bottom_toolbar — signature hint only; otherwise the row is hidden
# ---------------------------------------------------------------------------


def test_bottom_toolbar_returns_none_outside_prompt_session() -> None:
    """With no running prompt application `get_app()` raises — the
    toolbar function returns `None` so prompt_toolkit collapses the
    row instead of rendering a placeholder."""
    from robotcode.repl._pt.components import _bottom_toolbar

    assert _bottom_toolbar() is None


def test_spec_arg_items_flattens_argument_spec() -> None:
    """`_spec_arg_items` flattens a Robot ArgumentSpec to ordered labels,
    keeping `*args` / `**kwargs` markers and inlining defaults."""
    from types import SimpleNamespace

    from robotcode.repl._pt.components import _spec_arg_items

    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("message", "level"),
        var_positional=None,
        named_only=("html",),
        var_named="kwargs",
        defaults={"level": "INFO", "html": False},
    )
    items = _spec_arg_items(spec)
    assert items == ["message", "level='INFO'", "html=False", "**kwargs"]


def test_spec_arg_items_renders_varargs_marker() -> None:
    from types import SimpleNamespace

    from robotcode.repl._pt.components import _spec_arg_items

    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("list_",),
        var_positional="values",
        named_only=(),
        var_named=None,
        defaults={},
    )
    assert _spec_arg_items(spec) == ["list_", "*values"]


def test_render_signature_highlights_active_arg() -> None:
    """The keyword name carries `rf.keyword`; the active arg index
    carries `rf.toolbar.active-arg`; other args carry `rf.argument`."""
    from types import SimpleNamespace

    from robotcode.repl._pt.components import _render_signature

    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("message", "level"),
        var_positional=None,
        named_only=(),
        var_named=None,
        defaults={"level": "INFO"},
    )
    parts = _render_signature("Log", spec, active=1)
    styles = [s for s, _ in parts]
    texts = [t for _, t in parts]
    assert ("class:rf.keyword", "Log") in parts
    # Active arg has the active-arg style; the inactive arg the default one.
    assert "class:rf.toolbar.active-arg" in styles
    active_label = parts[styles.index("class:rf.toolbar.active-arg")][1]
    assert active_label == "level='INFO'"
    assert "class:rf.argument" in styles
    # The keyword name is followed by a separator.
    assert "    " in texts


def test_render_signature_no_args_keyword_only() -> None:
    """A keyword without arguments renders just the name."""
    from types import SimpleNamespace

    from robotcode.repl._pt.components import _render_signature

    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=(),
        var_positional=None,
        named_only=(),
        var_named=None,
        defaults={},
    )
    parts = _render_signature("No Operation", spec, active=0)
    assert parts == [("class:rf.keyword", "No Operation")]


def test_bottom_toolbar_renders_signature_when_cursor_in_arg_cell(monkeypatch: pytest.MonkeyPatch) -> None:
    """When `get_app().current_buffer` reports a cursor in an argument
    cell and the keyword is known, the toolbar returns styled tuples
    with the keyword's signature."""
    from types import SimpleNamespace

    import robotcode.repl._pt.components as backend_mod

    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("message", "level"),
        var_positional=None,
        named_only=(),
        var_named=None,
        defaults={"level": "INFO"},
    )
    fake_kw = SimpleNamespace(name="Log", args=spec)

    fake_buffer = SimpleNamespace(text="Log    hi", cursor_position=9)
    fake_app = SimpleNamespace(current_buffer=fake_buffer)
    monkeypatch.setattr(backend_mod, "get_app", lambda: fake_app)
    monkeypatch.setattr(backend_mod, "lookup_keyword_doc", lambda name: fake_kw if name == "Log" else None)

    toolbar = backend_mod._bottom_toolbar()
    assert isinstance(toolbar, list)
    styles = [s for s, _ in toolbar]
    assert "class:rf.keyword" in styles
    assert "class:rf.toolbar.active-arg" in styles


def test_bottom_toolbar_returns_none_when_keyword_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cursor in arg cell but no matching keyword → toolbar hidden."""
    from types import SimpleNamespace

    import robotcode.repl._pt.components as backend_mod

    fake_buffer = SimpleNamespace(text="UnknownKW    hi", cursor_position=15)
    fake_app = SimpleNamespace(current_buffer=fake_buffer)
    monkeypatch.setattr(backend_mod, "get_app", lambda: fake_app)
    monkeypatch.setattr(backend_mod, "lookup_keyword_doc", lambda name: None)

    assert backend_mod._bottom_toolbar() is None


def test_bottom_toolbar_highlights_named_arg_by_spec_position(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the cursor sits in `name=value`, the bar highlights the
    spec position of `name`, not the cell index. So `Log    msg
    html=True` with the cursor on `html=True` lights up `html`, not
    `level` (which is what the positional cell index 1 would point at)."""
    from types import SimpleNamespace

    import robotcode.repl._pt.components as backend_mod

    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("message", "level", "html"),
        var_positional=None,
        named_only=(),
        var_named=None,
    )
    fake_kw = SimpleNamespace(name="Log", args=spec)

    text = "Log    msg    html=True"
    fake_buffer = SimpleNamespace(text=text, cursor_position=len(text))
    fake_app = SimpleNamespace(current_buffer=fake_buffer)
    monkeypatch.setattr(backend_mod, "get_app", lambda: fake_app)
    monkeypatch.setattr(backend_mod, "lookup_keyword_doc", lambda name: fake_kw if name == "Log" else None)

    toolbar = backend_mod._bottom_toolbar()
    assert toolbar is not None
    # Find which arg label carries `rf.toolbar.active-arg`.
    active = [text for style, text in toolbar if style == "class:rf.toolbar.active-arg"]
    assert active == ["html"]


def test_bottom_toolbar_keeps_positional_idx_for_unknown_named_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    """`name=value` where `name` is NOT a real arg → fall back to the
    positional cell index, since Robot would treat it as a literal
    positional value."""
    from types import SimpleNamespace

    import robotcode.repl._pt.components as backend_mod

    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("message", "level"),
        var_positional=None,
        named_only=(),
        var_named=None,
    )
    fake_kw = SimpleNamespace(name="Log", args=spec)

    # `foo=bar` in cell 1 — foo isn't a Log arg, so highlight the
    # positional slot at index 0 (= message).
    text = "Log    foo=bar"
    fake_buffer = SimpleNamespace(text=text, cursor_position=len(text))
    fake_app = SimpleNamespace(current_buffer=fake_buffer)
    monkeypatch.setattr(backend_mod, "get_app", lambda: fake_app)
    monkeypatch.setattr(backend_mod, "lookup_keyword_doc", lambda name: fake_kw if name == "Log" else None)

    toolbar = backend_mod._bottom_toolbar()
    assert toolbar is not None
    active = [text for style, text in toolbar if style == "class:rf.toolbar.active-arg"]
    assert active == ["message"]


def test_bottom_toolbar_returns_none_when_cursor_in_keyword_cell(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cursor still typing the keyword (cell 0) → no signature → row hidden."""
    from types import SimpleNamespace

    import robotcode.repl._pt.components as backend_mod

    fake_buffer = SimpleNamespace(text="Lo", cursor_position=2)
    fake_app = SimpleNamespace(current_buffer=fake_buffer)
    monkeypatch.setattr(backend_mod, "get_app", lambda: fake_app)

    assert backend_mod._bottom_toolbar() is None


def test_prompt_toolkit_interpreter_get_history_reads_from_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`get_history()` reflects the file content in oldest → newest order."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c"])
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)
    interp = PromptToolkitConsoleInterpreter(app=None)
    assert interp.get_history() == ["a", "b", "c"]


def test_prompt_toolkit_interpreter_clear_history_truncates_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b"])
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)
    interp = PromptToolkitConsoleInterpreter(app=None)
    interp.clear_history()
    assert histfile.read_text() == ""
    assert interp.get_history() == []


def test_prompt_toolkit_interpreter_delete_history_entry_removes_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    histfile = tmp_path / "h"
    _seed_history(histfile, ["first", "second", "third"])
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)
    interp = PromptToolkitConsoleInterpreter(app=None)
    assert interp.delete_history_entry(2) is True
    assert interp.get_history() == ["first", "third"]


def test_prompt_toolkit_interpreter_delete_history_entry_out_of_range_returns_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    histfile = tmp_path / "h"
    _seed_history(histfile, ["only"])
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)
    interp = PromptToolkitConsoleInterpreter(app=None)
    assert interp.delete_history_entry(99) is False
    assert interp.delete_history_entry(0) is False
    assert interp.get_history() == ["only"]


def test_prompt_toolkit_interpreter_history_no_history_mode_is_read_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With `no_history=True`, the file is never written: clear/delete short-circuit."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b"])
    pristine = histfile.read_text()
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)

    interp = PromptToolkitConsoleInterpreter(app=None, no_history=True)
    interp.clear_history()
    assert interp.delete_history_entry(1) is False
    # File untouched.
    assert histfile.read_text() == pristine


def test_prompt_toolkit_interpreter_read_line_delegates_to_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`read_line` forwards prompt + `default=prefill` to PromptSession.prompt."""
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: tmp_path / "h")
    interp = PromptToolkitConsoleInterpreter(app=None)

    captured: List[dict[str, Any]] = []

    def fake_prompt(prompt_text: str, **kwargs: Any) -> str:
        captured.append({"prompt": prompt_text, **kwargs})
        return "user input"

    monkeypatch.setattr(interp._session, "prompt", fake_prompt)

    result = interp.read_line(">>> ", prefill="seed")
    assert result == "user input"
    assert len(captured) == 1
    call = captured[0]
    assert call["prompt"] == ">>> "
    assert call["default"] == "seed"
    # The doc viewer now runs as its own fullscreen Application, so
    # `read_line` no longer needs a `pre_run` hook to surface a Float —
    # `show_doc` blocks on `viewer._app.run()` instead.
    assert "pre_run" not in call


# ---------------------------------------------------------------------------
# `.history` dot-command — registered only on `PromptToolkitConsoleInterpreter`.
# On the plain interpreter typing `.history` falls through to the standard
# "Unknown dot-command" message.
# ---------------------------------------------------------------------------


class _StubApp:
    """Minimal app stub — only `.history` needs `app.echo` to capture output."""

    def __init__(self) -> None:
        self.messages: List[str] = []

    def echo(self, message: Any, **_: Any) -> None:
        self.messages.append(str(message))


def _make_pt_interpreter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, entries: List[str]) -> Any:
    """Build a `PromptToolkitConsoleInterpreter` whose history file is
    seeded with ``entries`` (oldest first). Returns ``(interpreter, app)``
    so the caller can drive `.history` and assert on `app.messages`."""
    histfile = tmp_path / "h"
    _seed_history(histfile, entries)
    monkeypatch.setattr("robotcode.repl.prompt_toolkit_interpreter.history_path", lambda: histfile)
    app = _StubApp()
    interp = PromptToolkitConsoleInterpreter(app=app)  # type: ignore[arg-type]
    return interp, app


def test_history_dotcommand_default_shows_last_20(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:

    interp, app = _make_pt_interpreter(monkeypatch, tmp_path, [f"line {i}" for i in range(1, 31)])
    interp._dispatch_dot_command(".history")
    blob = "\n".join(app.messages)
    # Should show entries 11..30 (the last 20).
    assert "line 30" in blob
    assert "line 11" in blob
    assert "line 10" not in blob


def test_history_dotcommand_n_shows_last_n(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:

    interp, app = _make_pt_interpreter(monkeypatch, tmp_path, [f"line {i}" for i in range(1, 11)])
    interp._dispatch_dot_command(".history 3")
    blob = "\n".join(app.messages)
    assert "line 10" in blob
    assert "line 9" in blob
    assert "line 8" in blob
    assert "line 7" not in blob


def test_history_dotcommand_clear_wipes_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:

    interp, app = _make_pt_interpreter(monkeypatch, tmp_path, ["a", "b"])
    interp._dispatch_dot_command(".history clear")
    assert interp.get_history() == []
    assert any("history cleared" in m for m in app.messages)


def test_history_dotcommand_del_n_removes_entry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:

    interp, app = _make_pt_interpreter(monkeypatch, tmp_path, ["one", "two", "three"])
    interp._dispatch_dot_command(".history del 2")
    assert interp.get_history() == ["one", "three"]
    assert any("deleted history entry 2" in m for m in app.messages)


def test_history_dotcommand_del_out_of_range_reports_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:

    interp, app = _make_pt_interpreter(monkeypatch, tmp_path, ["one"])
    interp._dispatch_dot_command(".history del 99")
    assert any("no history entry at index 99" in m for m in app.messages)


def test_history_dotcommand_del_missing_arg_prints_usage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:

    interp, app = _make_pt_interpreter(monkeypatch, tmp_path, ["one"])
    interp._dispatch_dot_command(".history del")
    assert any("usage: .history del" in m for m in app.messages)


def test_history_dotcommand_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:

    interp, app = _make_pt_interpreter(monkeypatch, tmp_path, [])
    interp._dispatch_dot_command(".history")
    assert any("no history" in m for m in app.messages)


def test_history_dotcommand_renders_multi_line_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Each newline-separated piece of an entry goes on its own
    indented line so the numbering stays readable."""

    entries = ["FOR    ${i}    IN RANGE    3\n    Log    ${i}\n    END"]
    interp, app = _make_pt_interpreter(monkeypatch, tmp_path, entries)
    interp._dispatch_dot_command(".history")
    # The first line carries the index; the next two lines are indented continuation.
    assert any(line.lstrip().startswith("1") and "FOR" in line for line in app.messages)
    assert any("Log    ${i}" in line for line in app.messages)
    assert any(line.strip() == "END" for line in app.messages)


def test_history_dotcommand_listed_in_help(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`.help` on the prompt_toolkit interpreter MUST list `.history` —
    the plain `test_dispatch_help_lists_all_commands` asserts the
    opposite (that plain mode omits it), so this is the matching
    positive check that the per-interpreter registry actually adds
    the subclass command."""
    interp, _ = _make_pt_interpreter(monkeypatch, tmp_path, [])
    assert "history" in type(interp)._dot_command_table()


def test_robot_completer_completes_dot_commands() -> None:
    """With `command_names`, a bare `.c` completes debugger/REPL commands."""
    completer = _RobotCompleter(command_names=["continue", "step", "catch"])
    comps = list(completer.get_completions(Document(".c"), CompleteEvent()))
    labels = [c.text for c in comps]
    assert labels == [".catch", ".continue"]  # c-prefixed, sorted; `step` excluded
    assert all(c.start_position == -2 for c in comps)  # replaces the typed `.c`


def test_robot_completer_threads_frame_context_to_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    """`context_provider` feeds the (context, variables) into the core service."""
    seen: List[Any] = []

    def fake_candidates(ctx: Any, *, context: Any = None, variables: Any = None, **_: Any) -> List[Any]:
        seen.append((context, variables))
        return []

    monkeypatch.setattr("robotcode.repl._pt.components.candidates_for_rich", fake_candidates)
    completer = _RobotCompleter(context_provider=lambda: ("CTX", "VARS"))
    list(completer.get_completions(Document("Lo"), CompleteEvent()))
    assert seen == [("CTX", "VARS")]
