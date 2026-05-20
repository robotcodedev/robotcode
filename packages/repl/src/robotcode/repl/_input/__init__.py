"""Backend abstraction for the REPL's interactive line-input.

`pick_backend()` walks a fallback cascade and returns the best
available implementation:

1. `PromptToolkitBackend` — if `prompt_toolkit>=3.0` is installed.
2. `ReadlineBackend` — if `readline` is importable (stdlib on Unix,
   transparent on Windows + Python 3.13+, or with `pyreadline3`).
3. `PlainBackend` — fallback that wraps the bare `input()`, preserving
   the historical behaviour with no history and no completion.

Each backend implements `read_line(prompt, multiline_continuation, prefill)`.
"""

from typing import Protocol

from ._plain import PlainBackend


class InputBackend(Protocol):
    """Protocol every line-input backend implements."""

    def read_line(
        self,
        prompt: str,
        *,
        multiline_continuation: bool = False,
        prefill: str = "",
    ) -> str:
        """Read a single line of input.

        Parameters
        ----------
        prompt:
            The prompt string to display. Backends may suppress it when
            stdin is not a TTY.
        multiline_continuation:
            True when the caller is inside a multi-line block (e.g.
            FOR/IF/TRY body) — backends may render a continuation
            prompt.
        prefill:
            Optional pre-filled text the user can edit. Used by Stage 4
            (auto-indent) to seed block-body lines with the right
            indent. Backends that have no editor (PlainBackend) ignore
            this.
        """
        ...


def pick_backend(*, no_history: bool = False, plain: bool = False) -> InputBackend:
    """Return the best available input backend.

    Parameters
    ----------
    no_history:
        When True, the readline / prompt_toolkit backends skip loading
        and saving the persistent history file — in-session arrow-up
        recall still works, but nothing crosses session boundaries.
        PlainBackend is unaffected (it has no history either way).
    plain:
        When True, bypass the cascade entirely and return PlainBackend.
        Disables completion, syntax highlighting, popup, auto-suggest,
        history — the prompt becomes a bare `input()`. Recommended for
        AI-agent invocations and automation pipelines where ANSI
        escapes or completion popups would corrupt stdout capture.

    The PlainBackend is always returnable, so this function never raises.
    """
    if plain:
        return PlainBackend()

    # PromptToolkit (Stage 3) — wins if the user installed the extra.
    try:
        from ._prompt_toolkit import PromptToolkitBackend  # type: ignore[import-not-found,import-untyped,unused-ignore]
    except ImportError:
        pass
    else:
        return PromptToolkitBackend(no_history=no_history)  # type: ignore[no-any-return,unused-ignore]

    # Readline (Stage 1+2) — stdlib on Unix, PyREPL on Win 3.13+.
    try:
        from ._readline import ReadlineBackend
    except ImportError:
        pass
    else:
        return ReadlineBackend(no_history=no_history)

    return PlainBackend()


__all__ = ["InputBackend", "PlainBackend", "pick_backend"]
