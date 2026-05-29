"""prompt_toolkit-driven REPL interpreter.

Subclasses `ConsoleInterpreter` and overrides the methods that benefit
from prompt_toolkit's editor surface:

- `read_line` runs the prompt through a `PromptSession` so the user
  gets completion popups, syntax highlighting, multi-line editing,
  reverse-search, signature toolbar, history-aware up-arrow recall.
- `show_doc` opens the markdown body in the fullscreen `DocViewer`
  Application (alternate-screen buffer) instead of dumping it into
  the scroll buffer.
- `get_history` / `clear_history` / `delete_history_entry` give
  `.history` direct access to the on-disk file history.
- F1 fires the `.help` dot-command through the same dispatcher path
  the user types `.help` into.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union
from urllib.parse import quote, unquote

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import History, InMemoryHistory
from robot import result, running

from robotcode.plugin import Application

from ._pt.components import (
    _DEFAULT_STYLE,
    _LOG_LEVEL_STYLES,
    _bottom_toolbar,
    _build_keybindings,
    _continuation_prompt,
    _on_completion_state_changed,
    _ReplFileHistory,
    _RobotCompleter,
)
from ._pt.doc_viewer import DocViewer
from ._pt.history import history_path
from ._pt.lexer import RobotLexer
from .base_interpreter import is_true
from .console_interpreter import ConsoleInterpreter, dot_command


class PromptToolkitConsoleInterpreter(ConsoleInterpreter):
    """`ConsoleInterpreter` whose I/O runs through a prompt_toolkit Application.

    Inherits all dot-commands from `ConsoleInterpreter` and adds
    `.history` here — the dispatcher only exposes commands that are
    registered on the live interpreter type, so plain mode (the
    base class alone) doesn't surface `.history` at all and the
    standard "Unknown dot-command" message takes over.
    """

    def __init__(
        self,
        app: Optional[Application] = None,
        files: Optional[List[Path]] = None,
        show_keywords: bool = False,
        inspect: Optional[bool] = False,
        no_history: bool = False,
    ) -> None:
        super().__init__(
            app=app,
            files=files,
            show_keywords=show_keywords,
            inspect=inspect,
            no_history=no_history,
        )

        self._history_store: History
        if no_history:
            self._history_store = InMemoryHistory()
        else:
            path = history_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            self._history_store = _ReplFileHistory(str(path))

        # The doc viewer is a *separate* fullscreen Application — see
        # the module docstring of `_pt/doc_viewer.py`. We instantiate
        # it eagerly so the layout objects are built once. The link
        # resolver lets `kw:` links — emitted by the `.kw` keyword list
        # (see `_keyword_list_entry`) — open a keyword's page in place.
        self._doc_viewer = DocViewer(link_resolver=self._resolve_doc_link)

        self._session: PromptSession[str] = PromptSession(
            history=self._history_store,
            completer=_RobotCompleter(),
            auto_suggest=AutoSuggestFromHistory(),
            complete_while_typing=True,
            complete_in_thread=True,
            multiline=True,
            key_bindings=_build_keybindings(bind_help_key=True),
            prompt_continuation=_continuation_prompt,
            lexer=RobotLexer(),
            style=_DEFAULT_STYLE,
            bottom_toolbar=_bottom_toolbar,
        )
        self._session.default_buffer.on_completions_changed += _on_completion_state_changed

    # ------------------------------------------------------------------
    # `ConsoleInterpreter` overrides — same contract, richer surface.
    # ------------------------------------------------------------------

    def read_line(self, prompt: str, *, multiline_continuation: bool = False, prefill: str = "") -> str:
        del multiline_continuation  # PromptSession handles continuation inline
        return self._session.prompt(prompt, default=prefill)

    def show_doc(self, title: str, markdown: str) -> None:
        """Display ``markdown`` in the fullscreen doc viewer.

        Blocks until the user closes the viewer (Esc / q / Enter). The
        viewer switches the terminal to the alternate screen buffer
        for the duration, so the host prompt and its scrollback survive
        untouched. Safe to call from inside a dot-command handler that
        runs between two `read_line` invocations.
        """
        self._doc_viewer.run(title, markdown)

    def _keyword_list_entry(self, owner_name: str, kw_name: str) -> str:
        """Render a `.kw` list entry as a link into the keyword's page.

        The target encodes the explicit `Owner.Keyword` name (percent-
        encoded, since keyword names contain spaces) behind a `kw:`
        scheme that `_resolve_doc_link` turns back into documentation.
        Tab/Enter in the doc viewer then opens the keyword in place.
        """
        return f"- [{kw_name}](kw:{quote(f'{owner_name}.{kw_name}')})"

    def _resolve_doc_link(self, target: str) -> Optional[Tuple[str, str]]:
        """Resolve a `kw:<owner.keyword>` doc-viewer link to a keyword
        page; returns ``None`` for any other target so the viewer falls
        back to its anchor / external-URL handling."""
        if target.startswith("kw:"):
            return self._keyword_doc(unquote(target[3:]))
        return None

    def log_message(
        self,
        message: str,
        level: str,
        html: Union[str, bool] = False,
        timestamp: Union[datetime, str, None] = None,
    ) -> None:
        """Print a Robot log line styled by `_DEFAULT_STYLE` rf.log.* classes.

        Robot's logger fires `log_message` from inside `run_keyword`,
        which is *between* `read_line` calls — no `Application` is
        active, so `print_formatted_text` writes straight to the file
        argument without interfering with the prompt redraw.
        """
        del timestamp  # not surfaced; matches the click-based plain impl
        if self.app is None:
            return
        if not self.app.config.verbose and level in ("DEBUG", "TRACE"):
            return

        std_err = level in ("ERROR", "FAIL")
        if is_true(html):
            message = f"*HTML*{message}"

        style_class = _LOG_LEVEL_STYLES.get(level, "")
        prefix = "  " * self.indent
        fragments = FormattedText(
            [
                ("", f"{prefix}[ "),
                (style_class, level),
                ("", f" ] {message}"),
            ]
        )
        # `print_formatted_text` accepts a file kwarg and ignores ANSI
        # state from the (paused) prompt-toolkit Application. Match the
        # plain implementation's stdout/stderr split for ERROR/FAIL.
        print_formatted_text(
            fragments,
            style=_DEFAULT_STYLE,
            file=sys.__stderr__ if std_err else sys.__stdout__,
        )

    def message(
        self,
        message: str,
        level: str,
        html: Union[str, bool] = False,
        timestamp: Union[datetime, str, None] = None,
    ) -> None:
        if self.app is not None and self.app.config.verbose:
            self.log_message(message, level, html, timestamp)

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if not self.show_keywords or self.app is None:
            return
        prefix = "  " * self.indent
        args = "  ".join(result.args)
        fragments = FormattedText(
            [
                ("", prefix),
                ("class:rf.kw.indicator", "KEYWORD "),
                ("class:rf.keyword", f"{result.libname}.{result.kwname}"),
                ("", f"  {args}" if args else ""),
            ]
        )
        print_formatted_text(fragments, style=_DEFAULT_STYLE, file=sys.__stdout__)
        self.indent += 1

    # ------------------------------------------------------------------
    # History accessors + the `.history` dot-command. These exist *only*
    # on this subclass — the dispatcher's MRO walk gives the user the
    # standard "Unknown dot-command" message when they type `.history`
    # on the plain interpreter, which is honest: there's no history file
    # in plain mode.
    # ------------------------------------------------------------------

    def get_history(self) -> List[str]:
        return list(reversed(list(self._history_store.load_history_strings())))

    def clear_history(self) -> bool:
        if isinstance(self._history_store, _ReplFileHistory):
            return self._history_store.clear()
        return False

    def delete_history_entry(self, idx: int) -> bool:
        if not isinstance(self._history_store, _ReplFileHistory):
            return False
        return self._history_store.delete(idx)

    @dot_command("history")
    def _history(self, arg: str) -> None:
        """Show / manage history: .history [N] | .history clear | .history del <N>

        Show or manage the persistent REPL history. Entries are numbered
        so subsequent subcommands can refer to them by index.

        Usage:
          .history [N]        Show the last N entries (default 20).
          .history clear      Wipe all entries (in-memory + on-disk).
          .history del <N>    Delete a single entry by its 1-based index
                              (use `.history` to look up the number).

        Examples:
          .history 50
          .history del 12
        """
        if self.app is None:
            return
        tokens = arg.split()
        if tokens and tokens[0] == "clear":
            self.clear_history()
            self.app.echo("History cleared.")
            return
        if tokens and tokens[0] == "del":
            if len(tokens) < 2 or not tokens[1].lstrip("-").isdigit():
                self.app.echo("Usage: .history del <N>")
                return
            idx = int(tokens[1])
            if self.delete_history_entry(idx):
                self.app.echo(f"Deleted history entry {idx}.")
            else:
                self.app.echo(f"No history entry at index {idx}.")
            return

        n = int(tokens[0]) if tokens and tokens[0].isdigit() else 20
        entries = self.get_history()
        if not entries:
            self.app.echo("(no history)")
            return
        start = max(0, len(entries) - n)
        width = len(str(len(entries)))
        for i in range(start, len(entries)):
            first, *rest = entries[i].split("\n")
            self.app.echo(f"  {i + 1:>{width}}  {first}")
            for line in rest:
                self.app.echo(f"  {' ' * width}  {line}")
