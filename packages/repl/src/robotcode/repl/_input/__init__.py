"""Backend abstraction for the REPL's interactive line-input.

Two implementations, picked by `pick_backend()`:

1. `PromptToolkitBackend` — if `prompt_toolkit>=3.0` is installed
   (via the ``[prompt-toolkit]`` extra). Rich editor with completion
   popup, syntax highlighting, history, signature toolbar.
2. `PlainBackend` — fallback. A thin wrapper around the built-in
   `input()`, with no editing features.

The `InputProvider` protocol only mandates `read_line`. History and
dispatcher methods live as concrete methods on `PromptToolkitBackend`
only; consumers reach for them via `hasattr` capability checks.
"""

from typing import Protocol

from ._plain import PlainBackend


class BackendUnavailableError(ImportError):
    """Raised when an explicitly requested backend cannot be imported.

    Subclasses `ImportError` so callers can catch either — `cli.py`
    translates it into a `click.UsageError` with a `pip install` hint.
    """


class InputProvider(Protocol):
    """The minimum every input backend implements: read a single line."""

    def read_line(
        self,
        prompt: str,
        *,
        multiline_continuation: bool = False,
        prefill: str = "",
    ) -> str:
        """Read one line of input.

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
            Optional pre-filled text the user can edit. Used by
            auto-indent to seed block-body lines with the right indent.
            Backends that have no editor (PlainBackend) ignore this.
        """
        ...


BACKEND_CHOICES = ("auto", "prompt-toolkit", "plain")


def pick_backend(*, no_history: bool = False, backend: str = "auto") -> InputProvider:
    """Return an input backend.

    Parameters
    ----------
    no_history:
        When True, the prompt_toolkit backend skips loading and saving the
        persistent history file — in-session arrow-up recall still works,
        but nothing crosses session boundaries. PlainBackend ignores this
        (it has no history either way).
    backend:
        One of ``"auto"``, ``"prompt-toolkit"``, ``"plain"``. ``"auto"``
        prefers prompt_toolkit if installed, else falls back to plain.
        Explicit ``"prompt-toolkit"`` raises `BackendUnavailableError`
        when the extra isn't installed — no silent fallback, so the
        caller learns that the explicit choice was not honoured.
    """
    if backend == "plain":
        return PlainBackend()

    if backend not in ("auto", "prompt-toolkit"):
        raise ValueError(f"Unknown backend: {backend!r}. Choose from {BACKEND_CHOICES}.")

    try:
        from ._prompt_toolkit import (
            PromptToolkitBackend,  # type: ignore[import-not-found,import-untyped,unused-ignore]
        )
    except ImportError as exc:
        if backend == "prompt-toolkit":
            raise BackendUnavailableError(
                "prompt_toolkit backend requested but not installed. "
                "Install with: pip install 'robotcode-repl[prompt-toolkit]'"
            ) from exc
        return PlainBackend()
    return PromptToolkitBackend(no_history=no_history)  # type: ignore[no-any-return,unused-ignore]


__all__ = ["BACKEND_CHOICES", "BackendUnavailableError", "InputProvider", "PlainBackend", "pick_backend"]
