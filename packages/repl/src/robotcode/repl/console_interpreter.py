import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, List, Optional, Union

import click
from robot import result, running
from robot.running import Keyword
from robot.running.context import EXECUTION_CONTEXTS

from robotcode.plugin import Application

from ._indent import compute_indent
from ._input import InputBackend, pick_backend
from .base_interpreter import BaseInterpreter, is_true


class ConsoleInterpreter(BaseInterpreter):
    def __init__(
        self,
        app: Optional[Application],
        files: Optional[List[Path]] = None,
        show_keywords: bool = False,
        inspect: Optional[bool] = False,
        no_history: bool = False,
        backend: str = "auto",
    ) -> None:
        super().__init__()

        self.app = app
        self.files = files
        self.show_keywords = show_keywords
        self.inspect = inspect

        self.executed_files: List[Path] = []
        self._input: InputBackend = pick_backend(no_history=no_history, backend=backend)
        # REPL inputs that parsed cleanly — `.save` exports them as a
        # runnable `.robot` file. Each entry may be multi-line.
        self._session_lines: List[str] = []
        # Wire the backend's F1 / future dispatcher-aware bindings into
        # the dot-command registry. Plain / readline backends don't
        # expose this method and are skipped.
        if hasattr(self._input, "bind_dispatcher") and self.app is not None:
            self._input.bind_dispatcher(self.app, self)

    def set_last_result(self, result: Any) -> None:
        """Mirror the last keyword's return value into Robot as ``${_}``.

        ``None`` results are skipped so noisy ``Log`` / ``Set Suite
        Variable`` calls don't wipe a meaningful previous value.
        """
        super().set_last_result(result)
        if result is None:
            return
        ctx = EXECUTION_CONTEXTS.current
        if ctx is None:
            return
        try:
            ctx.variables["${_}"] = result
        except Exception:
            # Locked scope / shutdown phase — drop the binding rather
            # than crash the REPL.
            pass

    def get_input(self) -> Iterator[Optional[Keyword]]:
        if self.executed_files and not self.files and not self.inspect:
            raise EOFError

        if self.files:
            file = self.files.pop(0)

            self.executed_files.append(file)

            text = file.read_text(encoding="utf-8")

            test, errors = self.get_test_body_from_string(text)
            if errors:
                return

            for kw in test.body:
                yield kw
        else:
            lines: List[str] = []
            last_one = False
            while True:
                prompt = ""
                if sys.stdin.isatty():
                    prompt = ">>> " if not lines else "... "

                prefill = compute_indent(lines) if lines else ""
                try:
                    text = self._input.read_line(
                        prompt,
                        multiline_continuation=bool(lines),
                        prefill=prefill,
                    )
                    if len(lines) == 0 and text == "":
                        break
                    # Only at the start of a fresh input — inside a
                    # multi-line block `.foo` could be a user keyword
                    # name and shouldn't be shadowed.
                    if not lines and text.lstrip().startswith(".") and self.app is not None:
                        from ._dot_commands import dispatch

                        if dispatch(text, self.app, self):
                            return
                except KeyboardInterrupt:
                    if len(lines) > 0:
                        lines = []
                        last_one = False
                        continue
                    raise

                lines.append(text)

                test, errors = self.get_test_body_from_string("\n".join(lines))

                if len(lines) > 1 and lines[-1] == "" and text == "":
                    last_one = True

                if errors:
                    if not last_one:
                        continue

                # Record cleanly-parsed inputs for `.save`. Error-only
                # inputs are skipped so the exported file stays runnable.
                if test.body:
                    self._session_lines.append("\n".join(lines))

                for kw in test.body:
                    yield kw

                break

    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        if self.app is None:
            return

        if not self.app.config.verbose and level in ["DEBUG", "TRACE"]:
            return

        std_err = level in ["ERROR", "FAIL"]

        if level == "INFO":
            level = click.style("INFO", fg="green")
        elif level == "WARN":
            level = click.style("WARN", fg="yellow")
        elif level == "ERROR":
            level = click.style("ERROR", fg="red")
        elif level == "FAIL":
            level = click.style("FAIL", fg="red", bold=True)
        elif level == "SKIP":
            level = click.style("SKIP", dim=True)
        elif level == "DEBUG":
            level = click.style("DEBUG", fg="bright_black")
        elif level == "TRACE":
            level = click.style("TRACE", fg="bright_black", dim=True)

        if is_true(html):
            message = f"*HTML*{message}"

        self.app.echo(f"{'  ' * self.indent}[ {level} ] {message}", file=sys.__stdout__ if std_err else sys.__stderr__)

    def message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        if self.app is not None and self.app.config.verbose:
            self.log_message(message, level, html, timestamp)

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if not self.show_keywords:
            return

        if self.app is None:
            return

        self.app.echo(
            f"{'  ' * self.indent}KEYWORD {result.libname}.{result.kwname}  {'  '.join(result.args)}",
            file=sys.__stdout__,
        )
        self.indent += 1

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if not self.show_keywords:
            return

        if self.app is None:
            return

        self.indent -= 1
