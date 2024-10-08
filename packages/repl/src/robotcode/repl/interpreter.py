import sys
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple, Union, cast

import click
from robot.api import get_model
from robot.output import LOGGER
from robot.output import Message as OutputMessage
from robot.running import Keyword, TestCase, TestSuite
from robot.running.context import EXECUTION_CONTEXTS
from robot.running.signalhandler import _StopSignalMonitor

from robotcode.plugin import Application
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.ast import iter_nodes


def _register_signal_handler(self: Any, exsignum: Any) -> None:
    pass


# Monkey patching the _register_signal_handler method to disable robot's signal handling
_StopSignalMonitor._register_signal_handler = _register_signal_handler


if get_robot_version() >= (7, 0):

    def _run_keyword(kw: Keyword, context: Any) -> Any:
        return kw.run(context.steps[-1][1], context)

else:

    def _run_keyword(kw: Keyword, context: Any) -> Any:
        return kw.run(context)


TRUE_STRINGS = {"TRUE", "YES", "ON", "1"}


def is_true(value: Union[str, bool]) -> bool:
    if isinstance(value, str):
        return value.upper() in TRUE_STRINGS
    return bool(value)


class Interpreter:
    def __init__(self, app: Application, files: Optional[List[Path]] = None, inspect: Optional[bool] = False) -> None:
        self.app = app
        self.files = files
        self.inspect = inspect

        self.executed_files: List[Path] = []

    def check_for_errors(self, node: Any) -> List[str]:
        if hasattr(node, "tokens"):
            for token in node.tokens:
                if hasattr(token, "error") and token.error:
                    raise SyntaxError(token.error)

        if hasattr(node, "error") and node.error:
            return [node.error]

        if hasattr(node, "errors") and node.errors:
            return list(node.errors)

        return []

    def get_test_body_from_string(self, command: str) -> Tuple[TestCase, List[str]]:
        suite_str = (
            "*** Test Cases ***\nDummyTestCase423141592653589793\n  "
            + ("\n  ".join(command.split("\n")) if "\n" in command else command)
        ) + "\n"

        model = get_model(suite_str)
        suite: TestSuite = TestSuite.from_model(model)

        errors: List[str] = []

        for node in iter_nodes(model):
            errors.extend(self.check_for_errors(node))

        return cast(TestCase, suite.tests[0]), errors

    def get_input(self) -> Iterator[Optional[Keyword]]:
        if self.executed_files and not self.files and not self.inspect:
            yield None
            return

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
                    print()
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

    def run_keyword(self, kw: Keyword) -> Any:
        with LOGGER.delayed_logging:
            kw_result = None
            try:
                context = EXECUTION_CONTEXTS.current
                kw_result = _run_keyword(kw, context)
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass
            finally:
                messages: List[OutputMessage] = LOGGER._log_message_cache or []
                for msg in messages or ():
                    # hack to get and evaluate log level
                    listener: Any = next(iter(LOGGER), None)
                    if listener is None or listener._is_logged(msg.level):
                        self.log_message(msg.message, msg.level, msg.html, msg.timestamp)
                LOGGER._log_message_cache = []

            return kw_result

    def run(self) -> Any:
        has_input = True
        while has_input:
            try:
                for kw in self.get_input():
                    if kw is None:
                        has_input = False
                        break
                    self.set_last_result(self.run_keyword(kw))
            except EOFError:
                break
            except (SystemExit, KeyboardInterrupt):
                break
            except BaseException as e:
                self.log_message(str(e), "ERROR")
                break

    def set_last_result(self, result: Any) -> None:
        if result is None:
            return
        self.app.echo_via_pager(f"{result}")

    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Optional[str] = None
    ) -> None:
        level_msg = None

        if level == "INFO":
            level_msg = click.style("INFO", fg="green")
        elif level == "WARN":
            level_msg = click.style("WARN", fg="yellow")
        elif level == "ERROR":
            level_msg = click.style("ERROR", fg="red")
        elif level == "FAIL":
            level_msg = click.style("FAIL", fg="red", bold=True)
        elif level == "SKIP":
            level_msg = click.style("SKIP", dim=True)
        elif level == "DEBUG":
            level_msg = click.style("DEBUG", fg="bright_black")
        elif level == "TRACE":
            level_msg = click.style("TRACE", fg="bright_black", dim=True)

        msg = message if not is_true(html) else f"*HTML*{message}"
        self.app.echo_via_pager(f"[ {level_msg} ] {msg}" if level_msg else msg)

    def message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Optional[str] = None
    ) -> None:
        if self.app.config.verbose:
            self.log_message(message, level, html, timestamp)
