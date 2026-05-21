"""Tests for the `prompt_toolkit` REPL backend.

Skipped wholesale when `prompt_toolkit` isn't installed — Stage 3
makes the dependency optional, and the readline / plain backends
have their own coverage.
"""

from pathlib import Path
from typing import Any, List

import pytest

pytest.importorskip("prompt_toolkit")

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from robotcode.repl._input._prompt_toolkit import (
    PromptToolkitBackend,
    _ReadlineCompatHistory,
    _RobotCompleter,
)

# ---------------------------------------------------------------------------
# _ReadlineCompatHistory — round-trips the readline plain-text format.
# ---------------------------------------------------------------------------


def test_readline_compat_history_loads_newest_first(tmp_path: Path) -> None:
    """prompt_toolkit consumes the iterator newest-first."""
    histfile = tmp_path / "repl_history"
    histfile.write_text("first\nsecond\nthird\n")

    history = _ReadlineCompatHistory(histfile)
    assert list(history.load_history_strings()) == ["third", "second", "first"]


def test_readline_compat_history_skips_blank_lines(tmp_path: Path) -> None:
    histfile = tmp_path / "repl_history"
    histfile.write_text("a\n\n   \nb\n")

    history = _ReadlineCompatHistory(histfile)
    assert list(history.load_history_strings()) == ["b", "a"]


def test_readline_compat_history_load_missing_file_is_silent(tmp_path: Path) -> None:
    """A missing history file means 'no prior history' — no crash."""
    history = _ReadlineCompatHistory(tmp_path / "nope")
    assert list(history.load_history_strings()) == []


def test_readline_compat_history_store_appends(tmp_path: Path) -> None:
    histfile = tmp_path / "repl_history"
    history = _ReadlineCompatHistory(histfile)
    history.store_string("alpha")
    history.store_string("beta")

    assert histfile.read_text() == "alpha\nbeta\n"


def test_readline_compat_history_store_creates_parent_dirs(tmp_path: Path) -> None:
    histfile = tmp_path / "nested" / "subdir" / "repl_history"
    history = _ReadlineCompatHistory(histfile)
    history.store_string("only line")

    assert histfile.read_text() == "only line\n"


def test_readline_compat_history_store_ignores_blank(tmp_path: Path) -> None:
    """Blank / whitespace-only lines mustn't pollute the file."""
    histfile = tmp_path / "repl_history"
    history = _ReadlineCompatHistory(histfile)
    history.store_string("")
    history.store_string("   ")
    history.store_string("real entry")

    assert histfile.read_text() == "real entry\n"


def test_readline_compat_history_no_history_skips_load(tmp_path: Path) -> None:
    histfile = tmp_path / "repl_history"
    histfile.write_text("existing\n")

    history = _ReadlineCompatHistory(histfile, no_history=True)
    assert list(history.load_history_strings()) == []


def test_readline_compat_history_no_history_skips_store(tmp_path: Path) -> None:
    histfile = tmp_path / "repl_history"
    histfile.write_text("existing\n")

    history = _ReadlineCompatHistory(histfile, no_history=True)
    history.store_string("should not land")

    assert histfile.read_text() == "existing\n"


def test_readline_compat_history_round_trips_multi_line_entry(tmp_path: Path) -> None:
    """Bug fix: a multi-line buffer (FOR/IF/etc.) must survive a
    store-then-reload cycle as ONE entry, not get split into N
    separate single-line entries on the next session."""
    histfile = tmp_path / "repl_history"
    history = _ReadlineCompatHistory(histfile)

    multi_line = "FOR    ${i}    IN RANGE    3\n    Log    ${i}\nEND"
    history.store_string(multi_line)

    # New instance — simulates a fresh REPL session opening the file.
    reloaded = list(_ReadlineCompatHistory(histfile).load_history_strings())
    assert reloaded == [multi_line]


def test_readline_compat_history_file_stays_single_line_per_entry(tmp_path: Path) -> None:
    """Even with multi-line content, each stored entry must be exactly
    one line in the file — otherwise readline's own loader (used by
    the other backend if the user uninstalls prompt_toolkit) would
    parse it as separate entries."""
    histfile = tmp_path / "repl_history"
    history = _ReadlineCompatHistory(histfile)
    history.store_string("first\nentry\nwith\nnewlines")
    history.store_string("second-plain")

    on_disk = histfile.read_text()
    # Each store_string appends exactly one `\n`-terminated line.
    assert on_disk.count("\n") == 2, f"file: {on_disk!r}"
    # The multi-line content is encoded — actual newlines became `\n` escapes.
    assert "first\\nentry\\nwith\\nnewlines" in on_disk


def test_readline_compat_history_preserves_literal_backslash_n(tmp_path: Path) -> None:
    """A user typing literal `\\n` (backslash-n) must NOT decode back
    to a newline — the escape is unambiguous because backslashes get
    doubled at write time."""
    histfile = tmp_path / "repl_history"
    history = _ReadlineCompatHistory(histfile)

    # User typed two characters: backslash, then n. Not a newline.
    history.store_string("Log    \\n")

    reloaded = list(_ReadlineCompatHistory(histfile).load_history_strings())
    assert reloaded == ["Log    \\n"]


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


def test_prompt_toolkit_backend_uses_shared_history_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The backend's history must point at the *same* file the readline
    backend uses — that's how recall survives a backend swap."""
    shared = tmp_path / "shared_history"
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: shared)

    backend = PromptToolkitBackend()
    history = backend._session.history
    assert isinstance(history, _ReadlineCompatHistory)
    assert history._path == shared


def test_prompt_toolkit_backend_threads_no_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    histfile = tmp_path / "h"
    histfile.write_text("ancient_line\n")
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)

    backend = PromptToolkitBackend(no_history=True)
    history = backend._session.history
    assert list(history.load_history_strings()) == []
    history.store_string("nope")
    assert histfile.read_text() == "ancient_line\n"


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
    histfile.write_text("a\nb\nc\n")
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    backend = PromptToolkitBackend()
    assert backend.get_history() == ["a", "b", "c"]


def test_prompt_toolkit_backend_clear_history_truncates_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    histfile = tmp_path / "h"
    histfile.write_text("a\nb\n")
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    import robotcode.repl._history as history_mod

    monkeypatch.setattr(history_mod, "history_path", lambda: histfile)
    backend = PromptToolkitBackend()
    backend.clear_history()
    assert histfile.read_text() == ""
    assert backend.get_history() == []


def test_prompt_toolkit_backend_delete_history_entry_removes_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    histfile = tmp_path / "h"
    histfile.write_text("first\nsecond\nthird\n")
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    import robotcode.repl._history as history_mod

    monkeypatch.setattr(history_mod, "history_path", lambda: histfile)
    backend = PromptToolkitBackend()
    assert backend.delete_history_entry(2) is True
    assert backend.get_history() == ["first", "third"]
    assert "second" not in histfile.read_text()


def test_prompt_toolkit_backend_history_no_history_mode_is_read_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With `--no-history`, the file is never written: clear/delete are
    no-ops on disk."""
    histfile = tmp_path / "h"
    histfile.write_text("a\nb\n")
    monkeypatch.setattr("robotcode.repl._input._prompt_toolkit.history_path", lambda: histfile)
    import robotcode.repl._history as history_mod

    monkeypatch.setattr(history_mod, "history_path", lambda: histfile)
    backend = PromptToolkitBackend(no_history=True)
    backend.clear_history()
    backend.delete_history_entry(1)
    # File untouched, since both ops short-circuit in no-history mode.
    assert histfile.read_text() == "a\nb\n"


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
