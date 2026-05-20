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
# _bottom_toolbar — Stage 7 session-context status line
# ---------------------------------------------------------------------------


def test_bottom_toolbar_shows_rf_version_and_cwd() -> None:
    """Toolbar must always render the running RF version and cwd —
    no execution-context lookup needed."""
    from robotcode.repl._input._prompt_toolkit import _bottom_toolbar

    toolbar = _bottom_toolbar()
    assert "RF " in toolbar
    assert "cwd:" in toolbar


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
