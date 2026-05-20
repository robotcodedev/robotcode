"""Tests for the prompt_toolkit multi-line buffer + smart-Enter / Shift-Enter
key bindings. Stage 4 — exercises `_insert_indented_newline` directly on a
real `Buffer`, plus an end-to-end PromptSession test for the smart-Enter
submit / continue branches via a pipe input."""

from typing import Iterator

import pytest

pytest.importorskip("prompt_toolkit")

from prompt_toolkit.application import create_app_session
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput

from robotcode.repl._input._prompt_toolkit import (
    PromptToolkitBackend,
    _build_keybindings,
    _insert_indented_newline,
)


@pytest.fixture
def pipe_input() -> Iterator[PipeInput]:
    """prompt_toolkit's recommended testing fixture: wrap the entire
    test in an AppSession backed by a pipe-input + DummyOutput, so any
    PromptSession the code-under-test constructs inherits both."""
    with create_pipe_input() as inp:
        with create_app_session(input=inp, output=DummyOutput()):
            yield inp


# ---------------------------------------------------------------------------
# _insert_indented_newline — pure buffer-level helper, exercises compute_indent
# ---------------------------------------------------------------------------


def test_insert_indented_newline_into_empty_buffer() -> None:
    buf = Buffer()
    _insert_indented_newline(buf)
    # Empty buffer → depth 0 → no indent on next line.
    assert buf.text == "\n"


def test_insert_indented_newline_after_for_opens_indent() -> None:
    buf = Buffer()
    buf.text = "FOR    ${i}    IN RANGE    3"
    buf.cursor_position = len(buf.text)
    _insert_indented_newline(buf)
    assert buf.text == "FOR    ${i}    IN RANGE    3\n    "


def test_insert_indented_newline_nested_block() -> None:
    buf = Buffer()
    buf.text = "FOR    ${i}    IN RANGE    3\n    IF    ${i} == 1"
    buf.cursor_position = len(buf.text)
    _insert_indented_newline(buf)
    # Two openers — next line lives at depth 2 → 8 spaces.
    assert buf.text == "FOR    ${i}    IN RANGE    3\n    IF    ${i} == 1\n        "


def test_insert_indented_newline_balanced_block_no_indent() -> None:
    buf = Buffer()
    buf.text = "FOR    ${i}    IN RANGE    3\n    Log    ${i}\nEND"
    buf.cursor_position = len(buf.text)
    _insert_indented_newline(buf)
    assert buf.text.endswith("\nEND\n")  # back to depth 0, no indent


# ---------------------------------------------------------------------------
# Smart-Enter behaviour — block-aware submit vs. continue
# ---------------------------------------------------------------------------


def test_smart_enter_submits_when_no_open_block(pipe_input: PipeInput) -> None:
    """A complete single-line keyword call must commit on plain Enter."""
    # `\r` is Enter (Keys.ControlM) — triggers smart-submit.
    # Note: `\n` (Keys.ControlJ) is the *newline-insert* binding in our
    # multi-line setup, so it would NOT submit.
    pipe_input.send_text("Log To Console    hello\r")
    backend = PromptToolkitBackend(no_history=True)
    result = backend.read_line(">>> ")
    assert result == "Log To Console    hello"


def test_smart_enter_submits_when_block_is_balanced_via_alt_enter(pipe_input: PipeInput) -> None:
    """Alt-Enter (Esc+Enter) inserts a newline regardless of block state;
    a final plain Enter on a balanced buffer commits. End-to-end the user
    typed `FOR    ${i}    IN RANGE    1`, Alt-Enter, `Log    ${i}`,
    Alt-Enter, `END`, Enter → submit."""
    # `\x1b\r` is Alt-Enter (Esc then Enter) — inserts newline + indent
    # without submitting. The final `\r` is plain Enter, which lands on
    # a balanced buffer (FOR…END), so smart-submit commits.
    pipe_input.send_text("FOR    ${i}    IN RANGE    1\x1b\rLog    ${i}\x1b\rEND\r")
    backend = PromptToolkitBackend(no_history=True)
    result = backend.read_line(">>> ")
    # The buffer at submit time contains FOR…\n…\nEND with the
    # auto-indents that Alt-Enter inserted. We don't dictate exact
    # whitespace — assert structural pieces instead.
    assert result.startswith("FOR    ${i}    IN RANGE    1")
    assert "Log    ${i}" in result
    assert result.endswith("END")


# ---------------------------------------------------------------------------
# _build_keybindings — make sure the multi-line wiring is in place
# ---------------------------------------------------------------------------


def test_build_keybindings_registers_portable_newline_aliases() -> None:
    """Plain `enter` (smart submit) plus the two portable newline-insert
    aliases (`escape enter` for Alt-Enter, `c-j` for Ctrl-J) must all
    be bound. Shift-Enter is intentionally NOT bound — most terminals
    can't deliver it distinctly from plain Enter, so a binding would
    never fire portably.

    prompt_toolkit translates the key strings we pass to `kb.add(...)`
    into internal `Keys` enum values: `enter` → `Keys.ControlM`,
    `escape` → `Keys.Escape`, `c-j` → `Keys.ControlJ`.
    """
    kb = _build_keybindings()
    bound_key_lists = [[str(k) for k in b.keys] for b in kb.bindings]

    # Plain Enter (smart submit) — single-key binding, ControlM.
    assert ["Keys.ControlM"] in bound_key_lists, f"plain Enter missing — bound: {bound_key_lists}"

    # Alt-Enter — two-key binding (Escape, ControlM).
    assert ["Keys.Escape", "Keys.ControlM"] in bound_key_lists, f"Alt-Enter missing — bound: {bound_key_lists}"

    # Ctrl-J — single-key binding, ControlJ.
    assert ["Keys.ControlJ"] in bound_key_lists, f"Ctrl-J missing — bound: {bound_key_lists}"
