"""Tests for the `prompt_toolkit` REPL backend.

Skipped wholesale when `prompt_toolkit` isn't installed — the prompt_toolkit
extra is optional, and the plain backend has its own coverage.
"""

from pathlib import Path
from typing import Any, List

import pytest

pytest.importorskip("prompt_toolkit")

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory

from robotcode.repl._input._prompt_toolkit import (
    PromptToolkitBackend,
    _ReplFileHistory,
    _RobotCompleter,
)


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
    from robotcode.repl._completion import Candidate

    # Patch in the consumer namespace (see [[feedback-mock-where-used]]).
    # Stage 6 switched the completer to `candidates_for_rich` which
    # returns `Candidate(label, detail)` objects.
    monkeypatch.setattr(
        "robotcode.repl._input._prompt_toolkit.candidates_for_rich",
        lambda ctx: [Candidate("Log", "Log a message"), Candidate("Log To Console", "Log to stdout")],
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
        "robotcode.repl._input._prompt_toolkit.candidates_for_rich",
        lambda ctx: [],
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
    from robotcode.repl._completion import Candidate

    monkeypatch.setattr(
        "robotcode.repl._input._prompt_toolkit.candidates_for_rich",
        lambda ctx: [Candidate("Log", "Log a message with the given level")],
    )

    completer = _RobotCompleter()
    completions = list(completer.get_completions(Document("Lo"), CompleteEvent()))

    assert len(completions) == 1
    # prompt_toolkit stores display_meta as either FormattedText or
    # a plain string — coerce to str for the assertion.
    assert "Log a message" in str(completions[0].display_meta)


# ---------------------------------------------------------------------------
# PromptToolkitBackend — wiring smoke tests (no real terminal involved).
# ---------------------------------------------------------------------------


def test_prompt_toolkit_backend_uses_filehistory_at_history_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The backend wires a stock `FileHistory` against the file `history_path()` returns."""
    target = tmp_path / "h"
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: target)

    backend = PromptToolkitBackend()
    history = backend._session.history
    assert isinstance(history, FileHistory)
    assert Path(str(history.filename)) == target


def test_prompt_toolkit_backend_threads_no_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`no_history=True` swaps in an InMemoryHistory — the on-disk file is left alone."""
    from prompt_toolkit.history import InMemoryHistory

    histfile = tmp_path / "h"
    _seed_history(histfile, ["ancient_line"])
    pristine = histfile.read_text()
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)

    backend = PromptToolkitBackend(no_history=True)
    history = backend._session.history
    assert isinstance(history, InMemoryHistory)
    history.store_string("nope")
    # File untouched — InMemoryHistory writes to memory only.
    assert histfile.read_text() == pristine


def test_prompt_toolkit_backend_survives_malformed_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A history file in an unrecognised format must not crash startup.
    prompt_toolkit's FileHistory uses `errors='replace'` on UTF-8 decode
    and ignores lines that don't start with `+`, so we just inherit
    that behaviour — the file appears empty to the REPL and new entries
    get appended in the proper format."""
    histfile = tmp_path / "h"
    histfile.write_bytes(b"\xff\xfe legacy junk\nfirst\nsecond\n")
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)

    backend = PromptToolkitBackend()
    assert backend.get_history() == []


def test_prompt_toolkit_backend_caps_load_to_max_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`load_history_strings` is sliced to `max_entries` so prompt_toolkit
    only sees the newest N even if the file is externally oversized."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c", "d", "e"])
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    monkeypatch.setenv("ROBOTCODE_REPL_HISTORY_SIZE", "3")

    backend = PromptToolkitBackend()
    # Newest three survive in the load, oldest → newest order.
    assert backend.get_history() == ["c", "d", "e"]


def test_prompt_toolkit_backend_under_cap_returns_all_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When the file holds fewer entries than the cap, all of them load."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b"])
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    monkeypatch.setenv("ROBOTCODE_REPL_HISTORY_SIZE", "10")

    backend = PromptToolkitBackend()
    assert backend.get_history() == ["a", "b"]


def test_prompt_toolkit_backend_append_evicts_oldest_when_over_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When an `append_string` would push the file past the cap, the
    oldest entry is dropped on disk. Keeps the file bounded over a long
    interactive session, not just at startup."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c"])
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    monkeypatch.setenv("ROBOTCODE_REPL_HISTORY_SIZE", "3")

    backend = PromptToolkitBackend()
    # Sanity: we start at the cap.
    assert backend.get_history() == ["a", "b", "c"]
    # Adding one more should evict "a" (oldest).
    backend._session.history.append_string("d")
    assert backend.get_history() == ["b", "c", "d"]
    # And another append evicts "b".
    backend._session.history.append_string("e")
    assert backend.get_history() == ["c", "d", "e"]


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
    from robotcode.repl._input._prompt_toolkit import _bottom_toolbar

    assert _bottom_toolbar() is None


def test_spec_arg_items_flattens_argument_spec() -> None:
    """`_spec_arg_items` flattens a Robot ArgumentSpec to ordered labels,
    keeping `*args` / `**kwargs` markers and inlining defaults."""
    from types import SimpleNamespace

    from robotcode.repl._input._prompt_toolkit import _spec_arg_items

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

    from robotcode.repl._input._prompt_toolkit import _spec_arg_items

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

    from robotcode.repl._input._prompt_toolkit import _render_signature

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

    from robotcode.repl._input._prompt_toolkit import _render_signature

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

    import robotcode.repl._input._prompt_toolkit as backend_mod

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

    import robotcode.repl._input._prompt_toolkit as backend_mod

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

    import robotcode.repl._input._prompt_toolkit as backend_mod

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

    import robotcode.repl._input._prompt_toolkit as backend_mod

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

    import robotcode.repl._input._prompt_toolkit as backend_mod

    fake_buffer = SimpleNamespace(text="Lo", cursor_position=2)
    fake_app = SimpleNamespace(current_buffer=fake_buffer)
    monkeypatch.setattr(backend_mod, "get_app", lambda: fake_app)

    assert backend_mod._bottom_toolbar() is None


def test_prompt_toolkit_backend_get_history_reads_from_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`get_history()` reflects the file content in oldest → newest order."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b", "c"])
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    backend = PromptToolkitBackend()
    assert backend.get_history() == ["a", "b", "c"]


def test_prompt_toolkit_backend_clear_history_truncates_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b"])
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    backend = PromptToolkitBackend()
    backend.clear_history()
    assert histfile.read_text() == ""
    assert backend.get_history() == []


def test_prompt_toolkit_backend_delete_history_entry_removes_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    histfile = tmp_path / "h"
    _seed_history(histfile, ["first", "second", "third"])
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    backend = PromptToolkitBackend()
    assert backend.delete_history_entry(2) is True
    assert backend.get_history() == ["first", "third"]


def test_prompt_toolkit_backend_delete_history_entry_out_of_range_returns_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    histfile = tmp_path / "h"
    _seed_history(histfile, ["only"])
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    backend = PromptToolkitBackend()
    assert backend.delete_history_entry(99) is False
    assert backend.delete_history_entry(0) is False
    assert backend.get_history() == ["only"]


def test_prompt_toolkit_backend_history_no_history_mode_is_read_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With `no_history=True`, the file is never written: clear/delete short-circuit."""
    histfile = tmp_path / "h"
    _seed_history(histfile, ["a", "b"])
    pristine = histfile.read_text()
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)

    backend = PromptToolkitBackend(no_history=True)
    backend.clear_history()
    assert backend.delete_history_entry(1) is False
    # File untouched.
    assert histfile.read_text() == pristine


def test_prompt_toolkit_backend_read_line_delegates_to_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`read_line` forwards prompt + `default=prefill` to PromptSession.prompt."""
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: tmp_path / "h")
    backend = PromptToolkitBackend()

    captured: List[dict[str, Any]] = []

    def fake_prompt(prompt_text: str, **kwargs: Any) -> str:
        captured.append({"prompt": prompt_text, **kwargs})
        return "user input"

    monkeypatch.setattr(backend._session, "prompt", fake_prompt)

    result = backend.read_line(">>> ", prefill="seed")
    assert result == "user input"
    assert captured == [{"prompt": ">>> ", "default": "seed"}]
