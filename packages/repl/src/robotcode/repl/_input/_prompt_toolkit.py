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
from typing import Iterator

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import History
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.styles import Style

from .._completion import candidates_for, tokenize
from .._history import history_path
from .._indent import compute_indent, has_open_block
from ._lexer import RobotLexer


class _ReadlineCompatHistory(History):
    """File-backed history in readline's plain-text format.

    prompt_toolkit's stock ``FileHistory`` writes timestamped, prefixed
    entries readline can't parse. This shim keeps the file readable
    by both backends so users can swap between them — `pip install`
    `[prompt-toolkit]` today, uninstall tomorrow — without losing
    arrow-up history.
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
                lines = [line.rstrip("\n") for line in fh if line.strip()]
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
                fh.write(string + "\n")
        except OSError:
            # Disk full / permission denied / read-only FS — losing a
            # history entry beats crashing the REPL on exit.
            pass


class _RobotCompleter(Completer):
    """Adapts `candidates_for()` to prompt_toolkit's Completion protocol."""

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterator[Completion]:
        del complete_event
        text = document.text_before_cursor
        ctx = tokenize(text, len(text))
        labels = candidates_for(ctx)
        # `start_position` is signed and negative — it tells
        # prompt_toolkit how many chars *before* the cursor to replace
        # with the completion's text.
        start = ctx.replace_start - len(text)
        for label in labels:
            yield Completion(label, start_position=start)


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

    - `Enter` is *smart*: submits when the buffer has no open Robot
      block, otherwise inserts a newline with Auto-Indent so the user
      keeps typing inside the block. Mirrors the auto-multi-line
      behaviour of the readline backend, but lives inside one prompt.
    - `Alt-Enter` (`Esc` then `Enter`) and `Ctrl-J` *always* insert a
      newline with Auto-Indent, regardless of block state — useful
      when the user wants to add an extra statement to a block whose
      structure already balances (e.g. you typed `FOR…END` and then
      decide to add another step before submitting).

    Shift-Enter is *not* bound by default: most terminals send the
    same byte (`\\r`) for `S-Enter` as for plain `Enter`, so a binding
    would never fire portably. Terminals that emit a distinct sequence
    (iTerm2, Kitty, modern Windows Terminal with custom keymap, …)
    can be wired up by the user via their own `KeyBindings` if they
    really want it — but Alt-Enter and Ctrl-J are universally portable.
    """
    kb = KeyBindings()

    @kb.add("escape", "enter")
    @kb.add("c-j")
    def _insert_newline(event: KeyPressEvent) -> None:
        _insert_indented_newline(event.current_buffer)

    @kb.add("enter")
    def _smart_submit(event: KeyPressEvent) -> None:
        buf = event.current_buffer
        if has_open_block(buf.text):
            _insert_indented_newline(buf)
        else:
            buf.validate_and_handle()

    return kb


def _continuation_prompt(width: int, line_number: int, soft_wrapped: int) -> str:
    """Show `... ` on every continuation line of the multi-line buffer,
    matching the `>>> ` / `... ` pair the readline backend produces."""
    del line_number, soft_wrapped
    return ("... ").rjust(width)


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
        )

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
