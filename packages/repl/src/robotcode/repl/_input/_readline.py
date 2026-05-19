"""Readline-based input backend — adds persistent history.

Importing this module activates Python's `readline` (or `pyreadline3`
shim on Windows pre-3.13 if the user installed it). The mere act of
importing `readline` is what hooks line-editing into the built-in
`input()` — no extra wiring needed.

If `readline` isn't importable, this module raises `ImportError` at
load time so `pick_backend()` skips it.
"""

import readline  # type: ignore[import-not-found,unused-ignore]

from .._history import attach_save_on_exit, dedup_last_entry, load_into_readline


class ReadlineBackend:
    """Wraps `input()` with persistent, fish-style deduplicated history.

    Once `readline` is imported, the builtin `input()` honours it for
    line editing, arrow-up recall and Ctrl-R incremental search. We
    add fish-style dedup on top: when the user re-enters a line that's
    already in the history, the older occurrences are removed so the
    entry appears only once at its newest position.
    """

    def __init__(self) -> None:
        load_into_readline(readline)
        attach_save_on_exit(readline)

    def read_line(
        self,
        prompt: str,
        *,
        multiline_continuation: bool = False,
        prefill: str = "",
    ) -> str:
        del multiline_continuation, prefill  # Stage-4 hooks land here
        try:
            return input(prompt)
        finally:
            # `input()` (via readline) appends the line to history just
            # before returning, regardless of whether the user pressed
            # Enter on real content or hit Ctrl-C / EOF. Run dedup
            # unconditionally — `dedup_last_entry` short-circuits on
            # blank entries on its own.
            dedup_last_entry(readline)
