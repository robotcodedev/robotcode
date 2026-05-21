"""Readline-based input backend — adds persistent history.

Importing this module activates Python's `readline` (or `pyreadline3`
shim on Windows pre-3.13 if the user installed it). The mere act of
importing `readline` is what hooks line-editing into the built-in
`input()` — no extra wiring needed.

If `readline` isn't importable, this module raises `ImportError` at
load time so `pick_backend()` skips it.
"""

from typing import List, Optional

# Prefer `gnureadline` over stdlib `readline` when available. On macOS
# (and some Linux Pythons built via python-build-standalone / uv) the
# stdlib's `readline` is linked against libedit, which silently ignores
# the GNU-specific bindings we depend on (Tab→complete syntax,
# `set completion-query-items` etc.). The `gnureadline` PyPI package
# ships a real GNU libreadline + Python binding and resolves all those
# gaps transparently — drop-in replacement, same module API.
try:
    import gnureadline as readline  # type: ignore[import-not-found,unused-ignore]
except ImportError:
    import readline  # type: ignore[import-not-found,unused-ignore]

from .._completion import candidates_for, tokenize
from .._history import (
    attach_save_on_exit,
    dedup_last_entry,
    delete_history_line_in_file,
    load_into_readline,
    truncate_history_file,
)


def _is_libedit() -> bool:
    """True when Python's readline is backed by libedit instead of GNU readline.

    libedit (used by macOS' system Python and by venvs whose Python was
    built against it) accepts a completely different bind syntax —
    ``parse_and_bind("tab: complete")`` is silently ignored, leaving
    Tab as a literal whitespace insert. We have to detect the backend
    and emit the right binding so Tab triggers completion at all.

    Python 3.13+ exposes ``readline.backend``; older Pythons need the
    library-version sniff.
    """
    backend = getattr(readline, "backend", None)
    if backend is not None:
        return bool(backend == "editline")
    return "EditLine" in str(getattr(readline, "_READLINE_LIBRARY_VERSION", ""))


class ReadlineBackend:
    """Wraps `input()` with persistent, fish-style deduplicated history
    *and* Robot-aware tab completion.

    Once `readline` is imported, the builtin `input()` honours it for
    line editing, arrow-up recall and Ctrl-R incremental search. We
    layer on:

    - **fish-style dedup**: re-entering a line removes its older copies
      so arrow-up cycles through unique commands only.
    - **Tab-completion** for keyword names, variables (after `${` /
      `@{` / `&{` / `%{`), library names (after `Import Library`) and
      resource paths (after `Import Resource`). Robot's case +
      whitespace + underscore insensitive matching is used throughout.

    When `no_history=True`, the persistent history file is neither
    loaded nor saved. In-session recall still works because readline
    accumulates lines in its own ring buffer automatically.

    The candidate list is rendered with readline's default display —
    so multi-match completions show the full replaced cell on every
    row (`Import Library  Collections` / `Import Library  Colorama`
    / …). Users who want a polished display (popup, hidden prefix,
    Ctrl-R search, Multi-Line-Editor) can install ``prompt_toolkit``;
    `pick_backend()` will pick the richer backend automatically.
    """

    def __init__(self, *, no_history: bool = False) -> None:
        self._no_history = no_history
        if not no_history:
            load_into_readline(readline)
            attach_save_on_exit(readline)
        self._install_completer()

    # ------------------------------------------------------------------
    # History access — backs the `.history` dot-command. Reads from
    # readline's in-memory ring (always up-to-date with the current
    # session, even when --no-history is set) and writes through to
    # the shared on-disk file the prompt_toolkit backend also uses.
    # ------------------------------------------------------------------

    def get_history(self) -> List[str]:
        length = readline.get_current_history_length()
        # readline indices are 1-based.
        return [readline.get_history_item(i) or "" for i in range(1, length + 1)]

    def clear_history(self) -> None:
        readline.clear_history()
        if not self._no_history:
            truncate_history_file()

    def delete_history_entry(self, idx: int) -> bool:
        length = readline.get_current_history_length()
        if not (1 <= idx <= length):
            return False
        # `remove_history_item` is 0-based.
        readline.remove_history_item(idx - 1)
        if not self._no_history:
            delete_history_line_in_file(idx)
        return True

    def read_line(
        self,
        prompt: str,
        *,
        multiline_continuation: bool = False,
        prefill: str = "",
    ) -> str:
        del multiline_continuation
        # Seed the line with `prefill` (typically the indent string for
        # the next continuation line) via `set_pre_input_hook`. readline
        # fires the hook *after* drawing the prompt and *before* the
        # first read — `insert_text` puts the chars into the buffer so
        # the user's cursor sits past them, ready to keep typing.
        if prefill:

            def _seed() -> None:
                readline.insert_text(prefill)
                readline.redisplay()

            readline.set_pre_input_hook(_seed)
        try:
            return input(prompt)
        finally:
            if prefill:
                # Clear the hook so subsequent single-line reads don't
                # inherit a stale indent (would surface as ghost spaces
                # at the next `>>> ` prompt).
                readline.set_pre_input_hook(None)
            # `input()` (via readline) appends the line to history just
            # before returning, regardless of whether the user pressed
            # Enter on real content or hit Ctrl-C / EOF. Run dedup
            # unconditionally — `dedup_last_entry` short-circuits on
            # blank entries on its own.
            dedup_last_entry(readline)

    # ------------------------------------------------------------------
    # Completion machinery
    # ------------------------------------------------------------------

    def _install_completer(self) -> None:
        """Register the Robot-aware completer with readline.

        Setting `set_completer_delims("")` makes readline pass the
        entire line (up to the cursor) to the completer — we need that
        because Robot's cell separator is "2+ spaces or a tab", which
        readline's single-character delim model can't express. We then
        do our own tokenizing inside `tokenize()`.
        """
        readline.set_completer_delims("")
        readline.set_completer(self._complete)
        if _is_libedit():
            # libedit accepts a different bind syntax — without this
            # Tab is left as the default editor binding (which on libedit
            # inserts a literal tab character, making the completer look
            # dead). libedit ignores the `set show-all-if-ambiguous` /
            # `set completion-query-items` directives, so no point
            # emitting them; behaviour matches libedit defaults.
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
            # Show the candidate list on the first Tab press when matches
            # are ambiguous. Without this, multi-match completions ring
            # the bell twice and never reveal what's available — which
            # looks like "Tab does nothing" to the user.
            readline.parse_and_bind("set show-all-if-ambiguous on")
            readline.parse_and_bind("set completion-ignore-case on")
            # Suppress the "Display all NNN possibilities? (y or n)"
            # prompt — Robot's discovery legitimately returns hundreds
            # of entries (every Python module on sys.path) and the
            # yes/no dialog adds friction without useful information.
            readline.parse_and_bind("set completion-query-items 0")

    def _complete(self, text: str, state: int) -> Optional[str]:
        """Readline-protocol completer.

        Called once per candidate (`state=0,1,…`) for a single Tab
        press. We compute all matches on `state==0` and cache them on
        the instance; later calls just index into the cache.
        """
        del text  # we read the live buffer via `get_line_buffer()`
        if state == 0:
            self._matches = self._build_matches()
        if 0 <= state < len(self._matches):
            return self._matches[state]
        return None

    def _build_matches(self) -> List[str]:
        """Inspect the current line, compute completions, return the
        substituted full-line strings readline expects.

        With `set_completer_delims("")`, readline replaces the entire
        `line[:cursor]` with each returned candidate — so each match
        must be the full line *after* applying the completion.
        """
        line = readline.get_line_buffer()
        cursor = readline.get_endidx()
        ctx = tokenize(line, cursor)
        labels = candidates_for(ctx)
        stable_prefix = line[: ctx.replace_start]
        return [stable_prefix + label for label in labels]
