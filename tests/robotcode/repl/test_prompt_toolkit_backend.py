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
