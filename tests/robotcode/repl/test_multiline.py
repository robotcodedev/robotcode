"""Tests for the prompt_toolkit multi-line buffer + smart-Enter / Shift-Enter
key bindings. Stage 4 — exercises `_insert_indented_newline` directly on a
real `Buffer`, plus an end-to-end PromptSession test for the smart-Enter
submit / continue branches via a pipe input."""

from typing import Iterator

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput

from robotcode.repl._pt.components import (
    _accept_highlighted_completion,
    _build_keybindings,
    _insert_indented_newline,
)
from robotcode.repl.prompt_toolkit_interpreter import PromptToolkitConsoleInterpreter


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
    backend = PromptToolkitConsoleInterpreter(app=None, no_history=True)
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
    backend = PromptToolkitConsoleInterpreter(app=None, no_history=True)
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


def _make_completion_state(text: str, original_text: str, original_cursor: int):  # type: ignore[no-untyped-def]
    """Build a `CompletionState` matching prompt_toolkit's
    post-`go_to_completion` shape — original document remembers the
    user's pre-preview text and the chosen completion's start_position
    references it."""
    from prompt_toolkit.buffer import CompletionState
    from prompt_toolkit.completion import Completion as _Completion
    from prompt_toolkit.document import Document

    completion = _Completion(text, start_position=-len(original_text[:original_cursor]))
    return CompletionState(
        original_document=Document(original_text, original_cursor),
        completions=[completion],
        complete_index=0,
    )


def test_accept_highlighted_completion_keeps_preview_and_appends_cell_sep() -> None:
    """After Enter on the highlighted candidate, the preview text
    stays in place and the popup closes. For a keyword completion
    with nothing else on the line, a cell separator is appended so
    the user can immediately start typing arguments."""
    buf = Buffer()
    # Simulate prompt_toolkit's post-preview state: user typed `Lo`,
    # arrowed onto `Log`, popup-preview wrote `Log` into the buffer.
    buf.text = "Log"
    buf.cursor_position = 3
    fires: list[str] = []
    buf.on_text_insert += lambda _b: fires.append(buf.text)
    buf.complete_state = _make_completion_state("Log", "Lo", 2)

    _accept_highlighted_completion(buf)

    # Preview stays, cell separator appended, cursor sits past it
    # ready for argument input.
    assert buf.text == "Log  "
    assert buf.cursor_position == 5
    # Popup is closed, the on_text_insert from the cell-sep insert
    # used `fire_event=False` so the popup doesn't re-trigger.
    assert fires == [], f"on_text_insert fired {len(fires)} time(s) — popup would re-open"
    assert buf.complete_state is None


def test_accept_highlighted_completion_replaces_whole_keyword_cell() -> None:
    """Re-invoking completion in the middle of an existing keyword
    must replace the *whole* cell, not just the prefix before the
    cursor — picking `Log Many` while the buffer has
    `Log To Console` should leave `Log Many`, not `Log Many To Console`."""
    buf = Buffer()
    # prompt_toolkit's preview state: original was `Log To Console`,
    # cursor was at 3 (after `Log`), user picked `Log Many` whose
    # start_position=-3 replaces the `Log` prefix → preview becomes
    # `Log Many To Console`, cursor at end of `Log Many` (8).
    buf.text = "Log Many To Console"
    buf.cursor_position = 8
    buf.complete_state = _make_completion_state("Log Many", "Log To Console", 3)

    _accept_highlighted_completion(buf)

    # Forward text in the same cell got removed; cell separator added
    # since no argument followed.
    assert buf.text == "Log Many  "
    assert buf.cursor_position == 10
    assert buf.complete_state is None


def test_accept_highlighted_completion_preserves_existing_arguments() -> None:
    """When the keyword already has arguments (a real cell sep
    follows), we delete only the rest of the keyword cell — not the
    args — and *don't* append a cell sep (one's already there)."""
    buf = Buffer()
    # Original `Log To Console  arg`, cursor at 3. Picked `Log Many`.
    # Preview = `Log Many To Console  arg`, cursor at 8.
    buf.text = "Log Many To Console  arg"
    buf.cursor_position = 8
    buf.complete_state = _make_completion_state("Log Many", "Log To Console  arg", 3)

    _accept_highlighted_completion(buf)

    assert buf.text == "Log Many  arg"
    assert buf.cursor_position == 8
    assert buf.complete_state is None


def test_accept_highlighted_completion_no_cell_setup_for_non_keyword() -> None:
    """Variable / library / etc. completions don't get the cell-cleanup
    treatment — just close the popup."""
    buf = Buffer()
    # Preview: `Log    ${TEST_NAME}` — cursor inside the second cell
    # (argument context with a closed variable).
    buf.text = "Log    ${TEST_NAME}"
    buf.cursor_position = 19
    buf.complete_state = _make_completion_state("${TEST_NAME}", "Log    ${T", 10)

    _accept_highlighted_completion(buf)

    # No cell sep appended, no forward-delete — buffer untouched.
    assert buf.text == "Log    ${TEST_NAME}"
    assert buf.cursor_position == 19
    assert buf.complete_state is None


def test_on_completion_state_changed_drops_forward_tail() -> None:
    """When the popup opens mid-keyword-cell, the
    `original_document` is trimmed of forward-cell content so the
    candidate preview renders as `Log To Console  hello` instead of
    `Log To Consoleog  hello`."""
    from prompt_toolkit.buffer import CompletionState
    from prompt_toolkit.completion import Completion as _Completion
    from prompt_toolkit.document import Document

    from robotcode.repl._pt.components import _on_completion_state_changed

    buf = Buffer()
    # User has `Log  hello`, cursor between `L` and `o`.
    buf.text = "Log  hello"
    buf.cursor_position = 1
    buf.complete_state = CompletionState(
        original_document=Document("Log  hello", 1),
        completions=[_Completion("Log To Console", start_position=-1)],
        complete_index=None,
    )

    _on_completion_state_changed(buf)

    # Forward-cell `og` is gone from the original_document; the
    # post-cursor `  hello` (cell separator + next cell) survives.
    assert buf.complete_state is not None
    assert buf.complete_state.original_document.text == "L  hello"
    assert buf.complete_state.original_document.cursor_position == 1


def test_on_completion_state_changed_skips_non_keyword_context() -> None:
    """Variable / argument / import contexts don't get trimmed —
    the bug only manifests for mid-keyword-cell positions."""
    from prompt_toolkit.buffer import CompletionState
    from prompt_toolkit.completion import Completion as _Completion
    from prompt_toolkit.document import Document

    from robotcode.repl._pt.components import _on_completion_state_changed

    buf = Buffer()
    # Cursor is in an argument cell (`Log    arg`, cursor at end of `arg`).
    buf.text = "Log    arg"
    buf.cursor_position = 10
    buf.complete_state = CompletionState(
        original_document=Document("Log    arg", 10),
        completions=[_Completion("argument", start_position=-3)],
        complete_index=None,
    )

    _on_completion_state_changed(buf)

    # Untouched — not a keyword cell.
    assert buf.complete_state.original_document.text == "Log    arg"


def test_on_completion_state_changed_is_idempotent() -> None:
    """Re-firing the handler after the trim is a no-op — important
    because `on_completions_changed` fires on every arrow navigation,
    not just popup-open."""
    from prompt_toolkit.buffer import CompletionState
    from prompt_toolkit.completion import Completion as _Completion
    from prompt_toolkit.document import Document

    from robotcode.repl._pt.components import _on_completion_state_changed

    buf = Buffer()
    buf.text = "Log  hello"
    buf.cursor_position = 1
    buf.complete_state = CompletionState(
        original_document=Document("Log  hello", 1),
        completions=[_Completion("Log Many", start_position=-1)],
        complete_index=None,
    )

    _on_completion_state_changed(buf)
    after_first = buf.complete_state.original_document.text
    _on_completion_state_changed(buf)
    after_second = buf.complete_state.original_document.text
    assert after_first == after_second == "L  hello"


def test_on_completion_state_changed_snapshots_literal_even_outside_keyword() -> None:
    """The literal-original snapshot is taken for *any* completion
    context so Esc-revert works regardless of whether trim happened.
    Trim itself only fires for keyword + forward-cell content."""
    from prompt_toolkit.buffer import CompletionState
    from prompt_toolkit.completion import Completion as _Completion
    from prompt_toolkit.document import Document

    from robotcode.repl._pt.components import _on_completion_state_changed

    buf = Buffer()
    # Argument context — no trim should happen, but snapshot still taken.
    buf.text = "Log    arg"
    buf.cursor_position = 10
    buf.complete_state = CompletionState(
        original_document=Document("Log    arg", 10),
        completions=[_Completion("argument", start_position=-3)],
        complete_index=None,
    )

    _on_completion_state_changed(buf)

    # Literal snapshot is set regardless of context.
    assert getattr(buf.complete_state, "_literal_original", None) == ("Log    arg", 10)
    # Original_document untouched (no trim for argument context).
    assert buf.complete_state.original_document.text == "Log    arg"


def test_esc_after_arrow_reverts_to_literal_original() -> None:
    """User had `Log  hello` with cursor before the `o`, arrowed to a
    candidate (so a preview text replaced their buffer), then Esc:
    the buffer must come back to `Log  hello` (literal pre-popup
    state), not stay on the preview and not stay on the trimmed
    `L  hello`."""
    from prompt_toolkit.buffer import CompletionState
    from prompt_toolkit.completion import Completion as _Completion
    from prompt_toolkit.document import Document

    from robotcode.repl._pt.components import _on_completion_state_changed

    buf = Buffer()
    # 1. Literal state pre-popup.
    buf.text = "Log  hello"
    buf.cursor_position = 1
    # 2. Open the popup (fresh state, no preview yet).
    buf.complete_state = CompletionState(
        original_document=Document("Log  hello", 1),
        completions=[_Completion("Log To Console", start_position=-1)],
        complete_index=None,
    )
    # 3. Snapshot + trim runs.
    _on_completion_state_changed(buf)
    assert getattr(buf.complete_state, "_literal_original", None) == ("Log  hello", 1)
    # 4. User arrows. `go_to_completion` mutates `complete_index`,
    #    applies the preview text via `buf.document = …`, then
    #    re-attaches the same state object (so our `_literal_original`
    #    attribute survives — same Python object identity).
    buf.go_to_completion(0)
    assert buf.text == "Log To Console  hello"  # trimmed preview, no `og` tail
    assert getattr(buf.complete_state, "_literal_original", None) == ("Log  hello", 1)
    # 5. Esc-revert flow: read snapshot off state, restore document.
    snapshot = getattr(buf.complete_state, "_literal_original", None)
    assert snapshot is not None
    text, pos = snapshot
    buf.document = Document(text, pos)
    buf.cancel_completion()

    assert buf.text == "Log  hello"
    assert buf.cursor_position == 1
    assert buf.complete_state is None


def test_build_keybindings_does_not_shadow_ctrl_r_for_reverse_search() -> None:
    """`Ctrl-R` is prompt_toolkit's default reverse-history-search binding
    in Emacs mode. We must NOT add our own `c-r` binding — otherwise we
    accidentally disable a feature users expect from every modern REPL."""
    kb = _build_keybindings()
    bound_keys = [[str(k) for k in b.keys] for b in kb.bindings]
    assert ["Keys.ControlR"] not in bound_keys, (
        "Ctrl-R must stay unbound so prompt_toolkit's reverse-history-search runs."
    )


def test_build_keybindings_omits_f1_when_not_requested() -> None:
    """Default (``bind_help_key=False``) leaves F1 unbound — used in
    tests and any caller that doesn't want the shortcut wired."""
    kb = _build_keybindings()
    bound_keys = [[str(k) for k in b.keys] for b in kb.bindings]
    assert ["Keys.F1"] not in bound_keys


def test_build_keybindings_binds_f1_when_requested() -> None:
    """``bind_help_key=True`` installs the F1 → `.help` binding."""
    kb = _build_keybindings(bind_help_key=True)
    bound_keys = [[str(k) for k in b.keys] for b in kb.bindings]
    assert ["Keys.F1"] in bound_keys


def test_f1_types_help_into_buffer_and_submits() -> None:
    """F1 doesn't dispatch `.help` directly — that would try to run the
    doc viewer's separate fullscreen Application from inside the
    prompt's event loop (prompt_toolkit doesn't support nested
    `run()` calls). Instead F1 types `.help` into the buffer and
    submits, so the outer `get_input` loop dispatches it after the
    prompt cleanly exits."""
    kb = _build_keybindings(bind_help_key=True)
    f1_handler = next(b for b in kb.bindings if [str(k) for k in b.keys] == ["Keys.F1"]).handler

    submitted: list[str] = []

    class _FakeBuffer:
        text = ""

        def validate_and_handle(self) -> None:
            submitted.append(self.text)

    fake_buf = _FakeBuffer()
    event = type("Ev", (), {})()
    event.current_buffer = fake_buf
    f1_handler(event)

    assert fake_buf.text == ".help"
    assert submitted == [".help"]


def test_build_keybindings_registers_single_smart_tab() -> None:
    """`Tab` is bound to a single handler that dispatches by runtime
    state: popup-open → cycle to next candidate, popup-closed in
    argument cell → insert cell separator, popup-closed elsewhere →
    open the completion menu. We must NOT use two filtered bindings
    keyed on tokenize() — the first Tab applies a candidate's
    preview, which would re-classify the cursor as `argument` and
    switch the next Tab from "cycle" to "insert spaces"."""
    kb = _build_keybindings()
    tab_bindings = [b for b in kb.bindings if [str(k) for k in b.keys] == ["Keys.ControlI"]]
    assert len(tab_bindings) == 1, f"expected exactly 1 Tab binding, got {tab_bindings}"


def test_smart_tab_cycles_when_popup_open() -> None:
    """First Tab opened the popup and selected entry 0; the second
    Tab must call `complete_next` instead of re-evaluating the
    context filter (which would say 'argument' after the preview
    applied a closed `${var}` and switch to insert-cell-sep)."""
    from prompt_toolkit.buffer import CompletionState
    from prompt_toolkit.completion import Completion as _Completion
    from prompt_toolkit.document import Document

    buf = Buffer()
    buf.text = "Log  ${TEST_NAME}"  # preview already applied
    buf.cursor_position = 17
    buf.complete_state = CompletionState(
        original_document=Document("Log  ${", 7),
        completions=[
            _Completion("${TEST_NAME}", start_position=-2),
            _Completion("${SUITE_NAME}", start_position=-2),
        ],
        complete_index=0,
    )

    # Locate the Tab handler and invoke it directly.
    kb = _build_keybindings()
    handler = next(b.handler for b in kb.bindings if [str(k) for k in b.keys] == ["Keys.ControlI"])

    class _Ev:
        def __init__(self, b: Buffer) -> None:
            self.current_buffer = b

    handler(_Ev(buf))  # type: ignore[arg-type]

    # Cycled to entry 1 — not committed entry 0, not re-classified as
    # argument and inserted a cell separator.
    assert buf.complete_state is not None
    assert buf.complete_state.complete_index == 1


def test_build_keybindings_registers_escape_with_completion_filter() -> None:
    """`Escape` must be bound *only* when the completion popup is open,
    so it cancels the popup (VSCode-style) without breaking its
    role as a prefix for Alt-key chords when no popup is visible.
    """
    from prompt_toolkit.filters import has_completions

    kb = _build_keybindings()
    escape_bindings = [b for b in kb.bindings if [str(k) for k in b.keys] == ["Keys.Escape"]]
    assert escape_bindings, "Escape binding is missing entirely"

    # The single Escape binding must carry the `has_completions` filter
    # so it only fires when there's a popup to close.
    [binding] = escape_bindings
    # `filter` may be a composed filter; just verify it's not the
    # always-true default (which would make Esc fire as a normal
    # standalone key everywhere).
    assert binding.filter is not None
    # has_completions is the documented filter we want; the binding's
    # `filter` is exactly that (or wraps it). Comparing identity is
    # the simplest unambiguous check.
    assert binding.filter is has_completions, (
        f"Escape binding should be gated by `has_completions`, got: {binding.filter!r}"
    )
