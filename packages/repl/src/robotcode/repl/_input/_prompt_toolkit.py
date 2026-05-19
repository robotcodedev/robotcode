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
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import History

from .._completion import candidates_for, tokenize
from .._history import history_path


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


class PromptToolkitBackend:
    """Power-user backend on top of `PromptSession`.

    Most of the polish — candidate popup, Ctrl-R reverse search,
    bracket auto-match, Cursor-up/down inside multi-line buffers —
    comes from `PromptSession` directly; we just plug in the
    Robot-aware completer and a history shim that shares the
    readline backend's file.

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
        )

    def read_line(
        self,
        prompt: str,
        *,
        multiline_continuation: bool = False,
        prefill: str = "",
    ) -> str:
        del multiline_continuation  # Stage-5 hook lands here
        # `PromptSession.prompt` raises `KeyboardInterrupt` on Ctrl-C
        # and `EOFError` on Ctrl-D — same exceptions as the builtin
        # `input()`, so `ConsoleInterpreter`'s existing handlers cover
        # both without further glue.
        return self._session.prompt(prompt, default=prefill)
