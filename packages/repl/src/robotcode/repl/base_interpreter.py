import abc
import signal
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple, Union, cast

from robot.api import get_model
from robot.errors import ExecutionStatus
from robot.output import LOGGER
from robot.output import Message as OutputMessage
from robot.running import Keyword, TestCase, TestSuite
from robot.running.context import EXECUTION_CONTEXTS
from robot.running.signalhandler import STOP_SIGNAL_MONITOR, _StopSignalMonitor

from robotcode.core.utils.path import normalized_path
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.ast import iter_nodes

if TYPE_CHECKING:
    from robot import result, running


class ExecutionInterrupted(ExecutionStatus):
    pass


def _register_signal_handler(self: Any, exsignum: Any) -> None:
    pass


def _stop_signal_monitor_call(self: Any, signum: Any, frame: Any) -> None:
    if self._running_keyword:
        self._stop_execution_gracefully()


def _stop_signal_monitor_stop_execution_gracefully(self: Any) -> None:
    raise ExecutionInterrupted("Execution interrupted")


_patched = False


def _patch() -> None:
    global _patched
    if not _patched:
        # Monkey patching the _register_signal_handler method to disable robot's signal handling
        # _StopSignalMonitor._register_signal_handler = _register_signal_handler
        _StopSignalMonitor.__call__ = _stop_signal_monitor_call
        _StopSignalMonitor._stop_execution_gracefully = _stop_signal_monitor_stop_execution_gracefully

    _patched = True


if get_robot_version() >= (7, 0):

    def _run_keyword(kw: Keyword, context: Any) -> Any:
        return kw.run(context.steps[-1][1], context)

else:

    def _run_keyword(kw: Keyword, context: Any) -> Any:
        return kw.run(context)


if get_robot_version() < (7, 0):

    class InterpreterLogger:
        def __init__(self, interpreter: "BaseInterpreter") -> None:
            self.interpreter = interpreter
            self.enabled = False

        def log_message(self, message: OutputMessage) -> None:
            if not self.enabled:
                return
            self.interpreter.log_message(message.message, message.level, message.html, message.timestamp)

        def message(self, message: OutputMessage) -> None:
            if not self.enabled:
                return
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
        def __init__(self, interpreter: "BaseInterpreter") -> None:
            self.interpreter = interpreter
            self.enabled = False

        def log_message(self, message: OutputMessage) -> None:
            if not self.enabled:
                return
            self.interpreter.log_message(message.message, message.level, message.html, message.timestamp)

        def message(self, message: OutputMessage) -> None:
            if not self.enabled:
                return
            self.interpreter.message(message.message, message.level, message.html, message.timestamp)

        def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if not self.enabled:
                return
            self.interpreter.start_keyword(data, result)

        def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if not self.enabled:
                return
            self.interpreter.end_keyword(data, result)

        def start_body_item(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if not self.enabled:
                return
            self.interpreter.start_keyword(data, result)

        def end_body_item(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if not self.enabled:
                return
            self.interpreter.end_keyword(data, result)


class BaseInterpreter(abc.ABC):
    def __init__(self) -> None:
        _patch()

        self._logger = InterpreterLogger(self)
        LOGGER.register_logger(self._logger)
        self.last_result: Any = None
        self.indent = 0
        self.source: Optional[Path] = None

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

        curdir = normalized_path(self.source).parent if self.source is not None else Path.cwd()

        model = get_model(suite_str, curdir=str(curdir).replace("\\", "\\\\"))
        suite: TestSuite = TestSuite.from_model(model)

        errors: List[str] = []

        for node in iter_nodes(model):
            errors.extend(self.check_for_errors(node))

        return cast(TestCase, suite.tests[0]), errors

    @abc.abstractmethod
    def get_input(self) -> Iterator[Optional[Keyword]]: ...

    def run_keyword(self, kw: Keyword) -> Any:
        self.indent = 0
        context = EXECUTION_CONTEXTS.current
        try:
            return _run_keyword(kw, context)
        except (SystemExit, KeyboardInterrupt):
            raise
        except ExecutionStatus:
            raise
        except BaseException as e:
            self.log_message(f"{type(e)}: {e}", "ERROR", timestamp=datetime.now())  # noqa: DTZ005

    def interrupt(self) -> None:
        signal.raise_signal(signal.SIGINT)

    def run(self) -> Any:
        self._logger.enabled = True

        has_input = True
        try:
            while has_input:
                try:
                    self.run_input()
                except EOFError:
                    break
                except (SystemExit, KeyboardInterrupt):
                    break
                except ExecutionInterrupted as e:
                    self.log_message(str(e), "ERROR", timestamp=datetime.now())  # noqa: DTZ005
                except ExecutionStatus:
                    pass
                except BaseException as e:
                    self.log_message(str(e), "ERROR", timestamp=datetime.now())  # noqa: DTZ005
        finally:
            self._logger.enabled = False

    def run_input(self) -> None:
        for kw in self.get_input():
            with STOP_SIGNAL_MONITOR:
                if kw is None:
                    break
                self.set_last_result(self.run_keyword(kw))

    def set_last_result(self, result: Any) -> None:
        self.last_result = result

    @abc.abstractmethod
    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None: ...

    @abc.abstractmethod
    def message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None: ...

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        pass

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        pass


TRUE_STRINGS = {"TRUE", "YES", "ON", "1"}


def is_true(value: Union[str, bool]) -> bool:
    if isinstance(value, str):
        return value.upper() in TRUE_STRINGS
    return bool(value)
