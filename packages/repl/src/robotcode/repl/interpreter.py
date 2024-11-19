import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple, Union, cast

import click
from robot.api import get_model
from robot.errors import ExecutionStatus
from robot.output import LOGGER
from robot.output import Message as OutputMessage
from robot.running import Keyword, TestCase, TestSuite
from robot.running.context import EXECUTION_CONTEXTS
from robot.running.signalhandler import _StopSignalMonitor

from robotcode.plugin import Application
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.ast import iter_nodes

if TYPE_CHECKING:
    from robot import result, running


def _register_signal_handler(self: Any, exsignum: Any) -> None:
    pass


_patched = False


def _patch() -> None:
    global _patched
    if not _patched:
        # Monkey patching the _register_signal_handler method to disable robot's signal handling
        _StopSignalMonitor._register_signal_handler = _register_signal_handler

    _patched = True


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


if get_robot_version() < (7, 0):

    class InterpreterLogger:
        def __init__(self, interpreter: "Interpreter") -> None:
            self.interpreter = interpreter
            self.enabled = False

        def log_message(self, message: OutputMessage) -> None:
            self.interpreter.log_message(message.message, message.level, message.html, message.timestamp)

        def message(self, message: OutputMessage) -> None:
            self.interpreter.message(message.message, message.level, message.html, message.timestamp)

        def start_keyword(self, args: Any) -> None:
            if not self.enabled:
                return
            self.interpreter.start_keyword(args.data, args.result)

        def end_keyword(self, args: Any) -> None:
            if not self.enabled:
                return
            self.interpreter.end_keyword(args.data, args.result)

else:
    import robot.output.loggerapi  # pyright: ignore[reportMissingImports]

    class InterpreterLogger(robot.output.loggerapi.LoggerApi):  # type: ignore[no-redef]
        def __init__(self, interpreter: "Interpreter") -> None:
            self.interpreter = interpreter
            self.enabled = False

        def log_message(self, message: OutputMessage) -> None:
            self.interpreter.log_message(message.message, message.level, message.html, message.timestamp)

        def message(self, message: OutputMessage) -> None:
            self.interpreter.message(message.message, message.level, message.html, message.timestamp)

        def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if not self.enabled:
                return
            self.interpreter.start_keyword(data, result)

        def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if not self.enabled:
                return
            self.interpreter.end_keyword(data, result)


class Interpreter:
    def __init__(
        self,
        app: Optional[Application],
        files: Optional[List[Path]] = None,
        show_keywords: bool = False,
        inspect: Optional[bool] = False,
    ) -> None:
        _patch()

        self.app = app
        self.files = files
        self.show_keywords = show_keywords
        self.inspect = inspect

        self.executed_files: List[Path] = []

        self._logger = InterpreterLogger(self)
        LOGGER.register_logger(self._logger)

        self.indent = 0

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

    def run_keyword(self, kw: Keyword) -> Any:
        self.indent = 0
        context = EXECUTION_CONTEXTS.current
        return _run_keyword(kw, context)

    def run(self) -> Any:
        self._logger.enabled = True

        has_input = True
        while has_input:
            try:
                self.run_input()
            except EOFError:
                break
            except (SystemExit, KeyboardInterrupt):
                break
            except ExecutionStatus:
                pass
            except BaseException as e:
                self.log_message(str(e), "ERROR")

    def run_input(self) -> None:
        for kw in self.get_input():
            if kw is None:
                break
            self.set_last_result(self.run_keyword(kw))

    def set_last_result(self, result: Any) -> None:
        if result is None:
            return
        if self.app is not None:
            self.app.echo(f"{result}")

    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Optional[str] = None
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
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Optional[str] = None
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
