import sys
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional, Union

import click
from robot import result, running
from robot.running import Keyword

from robotcode.plugin import Application

from .base_interpreter import BaseInterpreter, is_true


class ConsoleInterpreter(BaseInterpreter):
    def __init__(
        self,
        app: Optional[Application],
        files: Optional[List[Path]] = None,
        show_keywords: bool = False,
        inspect: Optional[bool] = False,
    ) -> None:
        super().__init__()

        self.app = app
        self.files = files
        self.show_keywords = show_keywords
        self.inspect = inspect

        self.executed_files: List[Path] = []

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

                try:
                    text = input(prompt)
                    if len(lines) == 0 and text == "":
                        break
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

        self.app.echo(f"{'  '*self.indent}[ {level} ] {message}", file=sys.__stdout__ if std_err else sys.__stderr__)

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
            f"{'  '*self.indent}KEYWORD {result.libname}.{result.kwname}  {'  '.join(result.args)}", file=sys.__stdout__
        )
        self.indent += 1

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if not self.show_keywords:
            return

        if self.app is None:
            return

        self.indent -= 1
