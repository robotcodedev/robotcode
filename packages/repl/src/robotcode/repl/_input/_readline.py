"""Readline-based input backend — adds persistent history.

Importing this module activates Python's `readline` (or `pyreadline3`
shim on Windows pre-3.13 if the user installed it). The mere act of
importing `readline` is what hooks line-editing into the built-in
`input()` — no extra wiring needed.

If `readline` isn't importable, this module raises `ImportError` at
load time so `pick_backend()` skips it.
"""

import readline  # type: ignore[import-not-found,unused-ignore]

from .._history import attach_save_on_exit, load_into_readline


class ReadlineBackend:
    """Wraps `input()` with persistent line-history.

    Stage 2 will extend this with `set_completer` for tab-complete;
    until then it gives users arrow-up history recall and Ctrl-R
    incremental search for free, courtesy of readline's defaults.
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
        # Once `readline` is imported, built-in `input` honours it.
        return input(prompt)
