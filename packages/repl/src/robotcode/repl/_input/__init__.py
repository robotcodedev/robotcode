"""Backend abstraction for the REPL's interactive line-input.

`pick_backend()` picks an explicit backend when one is named, else
walks a fallback cascade and returns the best available implementation:

1. `PromptToolkitBackend` — if `prompt_toolkit>=3.0` is installed.
2. `ReadlineBackend` — if `readline` is importable (stdlib on Unix,
   transparent on Windows + Python 3.13+, or with `pyreadline3`).
3. `PlainBackend` — fallback that wraps the bare `input()`, preserving
   the historical behaviour with no history and no completion.

Each backend implements `read_line(prompt, multiline_continuation, prefill)`.
"""

from typing import List, Protocol

from ._plain import PlainBackend


class BackendUnavailableError(ImportError):
    """Raised when an explicitly requested backend cannot be imported.

    Subclasses `ImportError` so callers can catch either — `cli.py`
    translates it into a `click.UsageError` with a `pip install` hint.
    """


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

    def get_history(self) -> List[str]:
        """Return persistent history entries, oldest → newest.

        PlainBackend returns ``[]`` (no history). Readline /
        prompt_toolkit return the in-memory buffer that mirrors the
        history file.
        """
        ...

    def clear_history(self) -> None:
        """Drop all history entries (in-memory + on-disk).

        PlainBackend is a no-op. The other backends truncate the
        shared history file and the in-memory ring.
        """
        ...

    def delete_history_entry(self, idx: int) -> bool:
        """Delete the 1-based history entry at ``idx``.

        Returns ``True`` on success, ``False`` when ``idx`` is out of
        range. PlainBackend always returns ``False``.
        """
        ...


BACKEND_CHOICES = ("auto", "prompt-toolkit", "readline", "plain")


def pick_backend(*, no_history: bool = False, backend: str = "auto") -> InputBackend:
    """Return an input backend.

    Parameters
    ----------
    no_history:
        When True, the readline / prompt_toolkit backends skip loading
        and saving the persistent history file — in-session arrow-up
        recall still works, but nothing crosses session boundaries.
        PlainBackend is unaffected (it has no history either way).
    backend:
        One of ``"auto"``, ``"prompt-toolkit"``, ``"readline"``,
        ``"plain"``. ``"auto"`` runs the fallback cascade. The other
        values force a specific backend and raise
        `BackendUnavailableError` when that backend can't be imported
        — no silent fallback, so the caller learns that the explicit
        choice was not honoured.
    """
    if backend == "plain":
        return PlainBackend()

    if backend == "prompt-toolkit":
        try:
            from ._prompt_toolkit import (
                PromptToolkitBackend,  # type: ignore[import-not-found,import-untyped,unused-ignore]
            )
        except ImportError as exc:
            raise BackendUnavailableError(
                "prompt_toolkit backend requested but not installed. "
                "Install with: pip install 'robotcode-repl[prompt-toolkit]'"
            ) from exc
        return PromptToolkitBackend(no_history=no_history)  # type: ignore[no-any-return,unused-ignore]

    if backend == "readline":
        try:
            from ._readline import ReadlineBackend
        except ImportError as exc:
            raise BackendUnavailableError(
                "readline backend not available on this Python build. "
                "Install with: pip install 'robotcode-repl[gnureadline]'"
            ) from exc
        return ReadlineBackend(no_history=no_history)

    if backend == "auto":
        try:
            from ._prompt_toolkit import (
                PromptToolkitBackend,  # type: ignore[import-not-found,import-untyped,unused-ignore]
            )
        except ImportError:
            pass
        else:
            return PromptToolkitBackend(no_history=no_history)  # type: ignore[no-any-return,unused-ignore]

        try:
            from ._readline import ReadlineBackend
        except ImportError:
            pass
        else:
            return ReadlineBackend(no_history=no_history)

        return PlainBackend()

    raise ValueError(f"Unknown backend: {backend!r}. Choose from {BACKEND_CHOICES}.")


__all__ = ["BACKEND_CHOICES", "BackendUnavailableError", "InputBackend", "PlainBackend", "pick_backend"]
