"""prompt_toolkit-based input backend — candidate popup, Ctrl-R search,
fish-style auto-suggest, sane multi-line cursor movement.

Activated when `prompt_toolkit>=3.0` is installed via the optional
extra (`pip install robotcode-repl[prompt-toolkit]`). Without it,
this module raises `ImportError` at load time so `pick_backend()`
falls through to the readline backend.

The candidate sourcing reuses `_completion.candidates_for()` — same
Robot-aware tokenizing as the readline backend. History is a thin
shim that reads and writes the **same plain-text file** the readline
backend uses, so switching between the two backends preserves
arrow-up recall.
"""

from pathlib import Path
from typing import Any, Iterator, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import has_completions
from prompt_toolkit.history import History
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.styles import Style

from robotcode.robot.utils import get_robot_version_str

from .._completion import CELL_SEPARATOR, candidates_for_rich, find_cell_end, tokenize
from .._history import history_path
from .._indent import compute_indent, has_open_block
from ._lexer import RobotLexer


def _escape_for_history(text: str) -> str:
    r"""Encode `text` so it occupies exactly one line of the history file.

    readline's plain-text history format is one-entry-per-line — a
    raw ``\n`` inside a multi-line buffer (FOR…END) would split it
    into multiple bogus history entries on next load. We escape:

    - ``\\``  → ``\\\\``  (so the round-trip stays unambiguous)
    - ``\n``  → ``\\n``

    Order matters — backslashes are doubled *first* so the literal
    backslash-n we inject for newlines doesn't get unescaped further.
    """
    return text.replace("\\", "\\\\").replace("\n", "\\n")


def _unescape_from_history(text: str) -> str:
    r"""Inverse of `_escape_for_history`. Walks the string once so
    ``\\\\n`` decodes to literal ``\\n`` (backslash + n), not to a
    newline — the naive two-pass `replace` would corrupt that case.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


class _ReadlineCompatHistory(History):
    """File-backed history in readline's plain-text format.

    prompt_toolkit's stock ``FileHistory`` writes timestamped, prefixed
    entries readline can't parse. This shim keeps the file readable
    by both backends so users can swap between them — `pip install`
    `[prompt-toolkit]` today, uninstall tomorrow — without losing
    arrow-up history.

    Multi-line buffers (FOR/IF/TRY blocks typed as one input) survive
    a round-trip via simple ``\\n``-escape encoding (see
    `_escape_for_history`). The on-disk file stays valid for
    readline's loader — every entry is still exactly one line — but
    arrow-up brings the whole block back in one piece.
    """

    def __init__(self, path: Path, *, no_history: bool = False) -> None:
        super().__init__()
        self._path = path
        self._no_history = no_history

    def load_history_strings(self) -> Iterator[str]:
        if self._no_history:
            return
        try:
            with self._path.open(encoding="utf-8", errors="replace") as fh:
                lines = [_unescape_from_history(line.rstrip("\n")) for line in fh if line.strip()]
        except (FileNotFoundError, OSError):
            return
        # prompt_toolkit consumes the iterator newest-first.
        yield from reversed(lines)

    def store_string(self, string: str) -> None:
        if self._no_history or not string.strip():
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(_escape_for_history(string) + "\n")
        except OSError:
            # Disk full / permission denied / read-only FS — losing a
            # history entry beats crashing the REPL on exit.
            pass


class _RobotCompleter(Completer):
    """Adapts `candidates_for_rich()` to prompt_toolkit's Completion protocol.

    Each candidate's `detail` (first-line keyword docstring, import
    kind, variable repr) becomes the popup's `display_meta` — shown
    grey-italic next to the label so users can see *what* a keyword
    does without leaving the prompt.

    `suppress_once` is a one-shot fuse used by the Esc-revert path:
    when the Esc handler restores text via `buf.document = …`,
    `complete_while_typing` would normally re-fire and re-open the
    popup. Setting this flag right before the restore makes the next
    `get_completions` call yield nothing, closing that loop.
    """

    def __init__(self) -> None:
        super().__init__()
        self.suppress_once = False

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterator[Completion]:
        del complete_event
        if self.suppress_once:
            self.suppress_once = False
            return
        text = document.text_before_cursor
        ctx = tokenize(text, len(text))
        candidates = candidates_for_rich(ctx)
        # `start_position` is signed and negative — it tells
        # prompt_toolkit how many chars *before* the cursor to replace
        # with the completion's text.
        start = ctx.replace_start - len(text)
        for cand in candidates:
            yield Completion(cand.label, start_position=start, display_meta=cand.detail)


def _find_robot_completer(buf: Buffer) -> Optional["_RobotCompleter"]:
    """Walk past any wrapping completers (e.g. `ThreadedCompleter`)
    to find our `_RobotCompleter` instance — so the Esc handler can
    poke `suppress_once` on it."""
    c: Any = buf.completer
    while c is not None:
        if isinstance(c, _RobotCompleter):
            return c
        c = getattr(c, "completer", None)
    return None


def _accept_highlighted_completion(buf: Buffer) -> None:
    """Close the popup, keeping the highlighted candidate's preview.

    prompt_toolkit's menu writes the candidate's text into the buffer
    as a live preview when the user arrows onto it; clearing
    `complete_state` makes that preview permanent. Calling
    `apply_completion` here would re-do delete+insert from the wrong
    (post-preview) cursor and produce `LoLog`/`LLog` duplication.

    For *keyword* completions we then prep the cell for argument
    input: delete any leftover text in the current keyword cell (so a
    mid-cell completion replaces the whole keyword, not just the
    prefix) and append a cell separator if no argument follows yet.
    """
    buf.complete_state = None
    text = buf.text
    pos = buf.cursor_position
    if tokenize(text[:pos], pos).kind != "keyword":
        return
    cell_end = find_cell_end(text, pos)
    if cell_end > pos:
        buf.text = text[:pos] + text[cell_end:]
        buf.cursor_position = pos
    line_remaining = buf.text[buf.cursor_position :].split("\n", 1)[0]
    if not line_remaining:
        buf.insert_text(CELL_SEPARATOR, fire_event=False)


def _on_completion_state_changed(buf: Buffer) -> None:
    """Bookkeeping that runs whenever `complete_state` changes:

    1. **Snapshot the literal original** on `state` so the Esc-revert
       path can restore the buffer to exactly what it looked like
       before the popup opened (cell-trim below modifies
       `original_document`, so we can't recover the literal from
       there afterwards).
    2. **Trim the forward-cell** from `original_document` when the
       cursor sits mid-keyword-cell — prompt_toolkit's
       `Completion.start_position` only deletes text *before* the
       cursor; without this trim, picking `Log To Console` while the
       cursor sits before the `o` in `Log  hello` would render as
       `Log To Consoleog  hello`.

    Both steps fire only when the popup first opens
    (`complete_index is None`); arrow navigation re-fires this
    handler but we no-op on it.
    """
    state = buf.complete_state
    if state is None:
        return
    if state.complete_index is not None:
        return  # navigation, not a fresh popup
    if getattr(state, "_literal_original", None) is not None:
        return  # already snapshotted
    text = state.original_document.text
    pos = state.original_document.cursor_position
    state._literal_original = (text, pos)  # type: ignore[attr-defined]
    if tokenize(text[:pos], pos).kind != "keyword":
        return
    cell_end = find_cell_end(text, pos)
    if cell_end <= pos:
        return
    state.original_document = Document(text[:pos] + text[cell_end:], pos)


def _insert_indented_newline(buf: Buffer) -> None:
    """Append a newline followed by the Auto-Indent for the next line.

    `+ [""]` extends the line list with an empty sentinel so the
    indent is computed for the line the user is *about to type*, not
    the line they just finished. Module-level for direct unit-test
    access — the key-binding handlers in `_build_keybindings()` just
    forward to here.
    """
    indent = compute_indent([*buf.text.splitlines(), ""])
    buf.insert_text("\n" + indent)


def _build_keybindings() -> KeyBindings:
    """Bindings for the multi-line buffer:

    - `Enter` is smart: accepts a highlighted completion if the popup
      has one selected, else inserts a newline + auto-indent if a
      Robot block is open, else submits.
    - `Escape` closes an open completion popup. Gated by
      `has_completions` so Esc keeps its default Alt-chord-prefix
      role when no popup is visible. Uses `eager=True` so the
      dismiss is instant — without it prompt_toolkit waits for the
      chord-match timeout (up to ~2 s total) before reacting.
      Trade-off: Alt-Enter (Esc-Enter chord) does NOT fire while a
      popup is open. Use `Ctrl-J` to insert a newline instead — same
      effect, no chord conflict.
    - `Alt-Enter` (Esc Enter, *only* when no popup is visible) and
      `Ctrl-J` (any time) insert a newline + auto-indent regardless
      of block state — useful for adding a step to an
      already-balanced block.
    - `Tab` in argument context inserts a cell separator instead of
      triggering the completion popup. Robot has no meaningful
      argument-name completions, so Tab is repurposed as a typing
      accelerator. In keyword / variable / import contexts Tab keeps
      prompt_toolkit's default completion behaviour.

    Shift-Enter is not bound: most terminals send the same byte as
    plain Enter, so the binding couldn't fire portably. Alt-Enter
    and Ctrl-J work everywhere.
    """
    kb = KeyBindings()

    @kb.add("escape", "enter")
    @kb.add("c-j")
    def _insert_newline(event: KeyPressEvent) -> None:
        _insert_indented_newline(event.current_buffer)

    @kb.add("enter")
    def _smart_submit(event: KeyPressEvent) -> None:
        buf = event.current_buffer
        state = buf.complete_state
        if state is not None and state.current_completion is not None:
            _accept_highlighted_completion(buf)
            return
        if has_open_block(buf.text):
            _insert_indented_newline(buf)
        else:
            buf.validate_and_handle()

    @kb.add("escape", filter=has_completions, eager=True)
    def _cancel_completion(event: KeyPressEvent) -> None:
        # Instant dismiss — `eager=True` skips the chord-match timeout
        # that otherwise makes Esc feel sluggish (up to ~2 s). Cost:
        # Alt-Enter (Esc-Enter chord) is suppressed while the popup is
        # open; users should reach for Ctrl-J instead.
        buf = event.current_buffer
        state = buf.complete_state
        # If the user previewed a candidate (arrowed), restore the
        # literal buffer state from before the popup opened. The
        # snapshot lives on the CompletionState because
        # `_on_completion_state_changed` may have trimmed
        # `original_document` for clean preview navigation — so we
        # can't recover the literal from `original_document` alone.
        if state is not None and state.complete_index is not None:
            snapshot = getattr(state, "_literal_original", None)
            if snapshot is None:
                text = state.original_document.text
                pos = state.original_document.cursor_position
            else:
                text, pos = snapshot
            # Suppress complete_while_typing's re-trigger on the
            # restored text so the popup doesn't immediately come
            # back. The completer's one-shot fuse handles it.
            completer = _find_robot_completer(buf)
            if completer is not None:
                completer.suppress_once = True
            buf.document = Document(text, pos)
        buf.cancel_completion()

    @kb.add("tab")
    def _smart_tab(event: KeyPressEvent) -> None:
        # Tab's role depends on what's on screen, *and* on the buffer
        # context. The order matters: once a candidate preview has been
        # applied to the buffer, tokenize() would re-classify the cursor
        # as `argument` (closed `${var}` in cell 2), so a context-first
        # check would jump from "cycle" to "insert cell-sep" mid-cycle.
        # Popup-state-first keeps cycling sane.
        #
        # 1. Popup open → cycle to next candidate (and back to top after
        #    the last). prompt_toolkit's COLUMN-style menu navigates
        #    with arrow keys by default; we bind Tab here too because
        #    that's what users expect from IDE / readline conventions.
        # 2. No popup, argument cell → insert a cell separator so Tab
        #    works as a typing accelerator (no useful argument
        #    completions exist anyway).
        # 3. No popup, anything else → open the completion menu.
        buf = event.current_buffer
        if buf.complete_state:
            buf.complete_next()
            return
        text = buf.document.text_before_cursor
        if tokenize(text, len(text)).kind == "argument":
            buf.insert_text(CELL_SEPARATOR)
        else:
            buf.start_completion(insert_common_part=True)

    return kb


def _continuation_prompt(width: int, line_number: int, soft_wrapped: int) -> str:
    """Show `... ` on every continuation line of the multi-line buffer,
    matching the `>>> ` / `... ` pair the readline backend produces."""
    del line_number, soft_wrapped
    return ("... ").rjust(width)


def _bottom_toolbar() -> str:
    """Render the bottom status line: RF version + cwd.

    Called on every render cycle of the prompt — must stay cheap.
    """
    try:
        cwd = str(Path.cwd())
    except OSError:
        # Working directory was deleted under us — happens in CI
        # cleanup races. Drop the cwd rather than crash the toolbar.
        cwd = "?"
    return f" RF {get_robot_version_str()} · cwd: {cwd}"


# Default colour theme. Maps the style classes the `RobotLexer` emits
# (and the completion-popup default classes) to ANSI / true-colour
# CSS-style declarations. Spätere PR könnte env-var-/config-toggle
# für theme-switching nachreichen.
_DEFAULT_STYLE = Style.from_dict(
    {
        "rf.keyword": "#5fafd7 bold",
        "rf.argument": "",
        "rf.assign": "#d75f87",
        "rf.comment": "#5f5f5f italic",
        "rf.block": "#d78700 bold",
        "rf.bdd": "#d78700 italic",
        "rf.variable.brace": "#5fd7af",
        "rf.variable.name": "#af87d7",
        "rf.variable.extended": "#af87d7 italic",
        "rf.variable.operator": "#5fd7af",
        "rf.variable.type": "#d7af5f",
        "rf.variable.expr": "#d75faf bold",
        "rf.variable.python": "#af87d7",
    }
)


class PromptToolkitBackend:
    """Power-user backend on top of `PromptSession`.

    Most of the polish — candidate popup, Ctrl-R reverse search,
    bracket auto-match, Cursor-up/down inside multi-line buffers —
    comes from `PromptSession` directly; we just plug in the
    Robot-aware completer, a history shim that shares the readline
    backend's file, and multi-line key bindings that mirror Robot's
    block syntax (Smart-Enter / Shift-Enter / Auto-Indent).

    Completions appear **as you type** (`complete_while_typing=True`)
    and are computed in a background thread (`complete_in_thread=True`)
    so the UI never blocks on Robot's library / resource discovery.
    The expensive `complete_*_import(None, …)` calls are also cached
    for the lifetime of the session in `_completion._FULL_LIST_CACHE`,
    so even the first keystroke after `Import Library    ` only walks
    `sys.path` once.
    """

    def __init__(self, *, no_history: bool = False) -> None:
        self._session: PromptSession[str] = PromptSession(
            history=_ReadlineCompatHistory(history_path(), no_history=no_history),
            completer=_RobotCompleter(),
            auto_suggest=AutoSuggestFromHistory(),
            complete_while_typing=True,
            complete_in_thread=True,
            multiline=True,
            key_bindings=_build_keybindings(),
            prompt_continuation=_continuation_prompt,
            lexer=RobotLexer(),
            style=_DEFAULT_STYLE,
            bottom_toolbar=_bottom_toolbar,
        )
        # Hook the buffer so the completion state carries (a) a snapshot
        # of the literal original (for Esc-revert) and (b) a trimmed
        # original_document (for clean mid-keyword preview rendering).
        self._session.default_buffer.on_completions_changed += _on_completion_state_changed

    def read_line(
        self,
        prompt: str,
        *,
        multiline_continuation: bool = False,
        prefill: str = "",
    ) -> str:
        del multiline_continuation  # PromptSession handles continuation inline
        # `PromptSession.prompt` raises `KeyboardInterrupt` on Ctrl-C
        # and `EOFError` on Ctrl-D — same exceptions as the builtin
        # `input()`, so `ConsoleInterpreter`'s existing handlers cover
        # both without further glue.
        return self._session.prompt(prompt, default=prefill)
