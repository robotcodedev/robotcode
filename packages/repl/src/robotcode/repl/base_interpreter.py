import abc
import contextlib
import signal
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Protocol, Tuple, Union, cast

from robot.api import get_model
from robot.errors import ExecutionFailed, ExecutionPassed, ExecutionStatus
from robot.output import LOGGER
from robot.output import Message as OutputMessage
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import For, If, Try, While
from robot.parsing.model.statements import Error, Statement
from robot.result import Keyword as ResultKeyword
from robot.running import Keyword, TestCase, TestSuite
from robot.running.context import EXECUTION_CONTEXTS
from robot.running.signalhandler import STOP_SIGNAL_MONITOR, _StopSignalMonitor
from robot.utils import normalize

from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.ast import iter_nodes

if TYPE_CHECKING:
    from robot import result, running


class ExecutionObserver(Protocol):
    """A consumer of the interpreter's execution event stream.

    Registered via `BaseInterpreter.register_observer`; notified for every
    keyword/body-item start and end during a run (e.g. the debug controller),
    and for test/suite *ends* (needed for failed-test / failed-suite exception
    breakpoints). `data` is the running-model node, `result` the result-model
    node — the same pair Robot's logger delivers. On RF<7 the suite/test logger
    hook passes a single combined object, forwarded as both `data` and `result`.
    """

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None: ...

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None: ...

    def start_test(self, data: "running.TestCase", result: "result.TestCase") -> None: ...

    def end_test(self, data: "running.TestCase", result: "result.TestCase") -> None: ...

    def start_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None: ...

    def end_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None: ...


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


if RF_VERSION >= (7, 0):

    def _run_keyword(kw: Keyword, context: Any) -> Any:
        # A keyword typed at a stop becomes a child of the running step. At a stop
        # where no step runs any more, such as the end of a test, it goes to the
        # test, and without a test to a detached result.
        if context.steps:
            parent = context.steps[-1][1]
        else:
            parent = context.test if context.test is not None else ResultKeyword()
        return kw.run(parent, context)

else:

    def _run_keyword(kw: Keyword, context: Any) -> Any:
        return kw.run(context)


# The qualified name of a *keyword* result node — used to spot the `Repl` marker
# keyword and to label keyword stack frames. Control structures (FOR/IF/RETURN/…)
# are their own result classes, not `Keyword`, so `isinstance` excludes them
# cleanly (verified RF 5/6/7) without guessing at attributes. The version split
# is resolved once here, not per call: RF7 exposes the qualified name as
# `full_name`; RF<7 carries it on the (non-deprecated) `name`.
if RF_VERSION >= (7, 0):

    def _keyword_qualified_name(keyword: ResultKeyword) -> str:
        return cast(str, keyword.full_name)

else:

    def _keyword_qualified_name(keyword: ResultKeyword) -> str:
        return cast(str, keyword.name)


def result_qualified_name(result: Any) -> Optional[str]:
    return _keyword_qualified_name(result) if isinstance(result, ResultKeyword) else None


# Blocks that stay open until their END. Their branches (ELSE, EXCEPT, …) are blocks of
# the same classes with another header and never get an END of their own.
if RF_VERSION >= (7, 2):
    from robot.parsing.model.blocks import Group

    _END_BLOCKS: Tuple[Any, ...] = (For, While, If, Try, Group)
    _BLOCK_OPENERS = frozenset({Token.FOR, Token.WHILE, Token.IF, Token.TRY, Token.GROUP})
else:
    _END_BLOCKS = (For, While, If, Try)
    _BLOCK_OPENERS = frozenset({Token.FOR, Token.WHILE, Token.IF, Token.TRY})

# A REPL input runs as the body of the session test, so it can't have settings: neither
# test settings nor the keyword settings that a test reports as not allowed.
_SETTING_TYPES = frozenset(
    {Token.DOCUMENTATION, Token.TAGS, Token.SETUP, Token.TEARDOWN, Token.TEMPLATE, Token.TIMEOUT}
)
_SETTING_NAMES = frozenset({"documentation", "tags", "setup", "teardown", "template", "timeout", "arguments", "return"})


def _mark_settings_as_errors(test: Any) -> None:
    """Mark the settings of a REPL input as errors, as Robot Framework's lexer marks a
    setting a test can't have, so that Robot Framework reports them like a non-existing
    setting."""
    for i, node in enumerate(test.body):
        if not isinstance(node, Statement):
            continue
        if node.type in _SETTING_TYPES:
            node = test.body[i] = Error(
                [Token(Token.ERROR, t.value, t.lineno, t.col_offset) if t.type == node.type else t for t in node.tokens]
            )
        if isinstance(node, Error):
            for token in node.get_tokens(Token.ERROR):
                name = token.value[1:-1].strip() if token.value.startswith("[") and token.value.endswith("]") else ""
                if normalize(name) in _SETTING_NAMES:
                    token.error = f"Setting '{name}' is not allowed in the REPL."


@dataclass
class ReplInput:
    """REPL input parsed as a test body by `BaseInterpreter.parse_input`."""

    test: TestCase
    # The parse errors of the input.
    errors: List[str]
    # True while a block of the input lacks its END, so more lines can complete it.
    incomplete: bool


if RF_VERSION < (7, 0):

    class InterpreterLogger:
        def __init__(self, interpreter: "BaseInterpreter") -> None:
            self.interpreter = interpreter
            self.enabled = False
            # When forwarding is on for a runner-driven debug run, the runner's
            # own console shows suite output — so message echoing is muted to
            # avoid double output, independently of event forwarding.
            self.echo_messages = True

        def log_message(self, message: OutputMessage) -> None:
            if not self.enabled or not self.echo_messages:
                return
            self.interpreter.log_message(message.message, message.level, message.html, message.timestamp)

        def message(self, message: OutputMessage) -> None:
            if not self.enabled or not self.echo_messages:
                return
            self.interpreter.message(message.message, message.level, message.html, message.timestamp)

        def start_keyword(self, args: Any) -> None:
            if self.interpreter._maybe_trigger_repl(args.result):
                return
            if not self.enabled:
                return
            self.interpreter._notify_start_keyword(args.data, args.result)

        def end_keyword(self, args: Any) -> None:
            if not self.enabled:
                return
            self.interpreter._notify_end_keyword(args.data, args.result)

        def start_test(self, model: Any) -> None:
            # RF<7 passes a single combined model object (has `.status`/`.name`);
            # forward it as both data and result.
            if not self.enabled:
                return
            self.interpreter._notify_start_test(model, model)

        def start_suite(self, model: Any) -> None:
            if not self.enabled:
                return
            self.interpreter._notify_start_suite(model, model)

        def end_test(self, model: Any) -> None:
            if not self.enabled:
                return
            self.interpreter._notify_end_test(model, model)

        def end_suite(self, model: Any) -> None:
            if not self.enabled:
                return
            self.interpreter._notify_end_suite(model, model)

else:
    import robot.output.loggerapi  # pyright: ignore[reportMissingImports]

    class InterpreterLogger(robot.output.loggerapi.LoggerApi):  # type: ignore[no-redef]
        def __init__(self, interpreter: "BaseInterpreter") -> None:
            self.interpreter = interpreter
            self.enabled = False
            # When forwarding is on for a runner-driven debug run, the runner's
            # own console shows suite output — so message echoing is muted to
            # avoid double output, independently of event forwarding.
            self.echo_messages = True

        def log_message(self, message: OutputMessage) -> None:
            if not self.enabled or not self.echo_messages:
                return
            self.interpreter.log_message(message.message, message.level, message.html, message.timestamp)

        def message(self, message: OutputMessage) -> None:
            if not self.enabled or not self.echo_messages:
                return
            self.interpreter.message(message.message, message.level, message.html, message.timestamp)

        def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if self.interpreter._maybe_trigger_repl(result):
                return
            if not self.enabled:
                return
            self.interpreter._notify_start_keyword(data, result)

        def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if not self.enabled:
                return
            self.interpreter._notify_end_keyword(data, result)

        def start_body_item(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if self.interpreter._maybe_trigger_repl(result):
                return
            if not self.enabled:
                return
            self.interpreter._notify_start_keyword(data, result)

        def end_body_item(self, data: "running.Keyword", result: "result.Keyword") -> None:
            if not self.enabled:
                return
            self.interpreter._notify_end_keyword(data, result)

        def start_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
            if not self.enabled:
                return
            self.interpreter._notify_start_test(data, result)

        def start_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
            if not self.enabled:
                return
            self.interpreter._notify_start_suite(data, result)

        def end_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
            if not self.enabled:
                return
            self.interpreter._notify_end_test(data, result)

        def end_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
            if not self.enabled:
                return
            self.interpreter._notify_end_suite(data, result)


# The interpreter whose prompt loop started last. `_maybe_trigger_repl` sets it when
# the `repl` marker keyword starts; the marker's body takes it once the loop has returned.
_active_interpreter: Optional["BaseInterpreter"] = None


def take_active_interpreter() -> Optional["BaseInterpreter"]:
    """Return the interpreter whose prompt loop started last and forget it, so a later
    session in the same process never sees it."""
    global _active_interpreter
    interpreter, _active_interpreter = _active_interpreter, None
    return interpreter


class BaseInterpreter(abc.ABC):
    def __init__(self) -> None:
        _patch()

        self._logger = InterpreterLogger(self)
        LOGGER.register_logger(self._logger)
        self.last_result: Any = None
        self.indent = 0
        self.source: Optional[Path] = None
        self._curdir: Optional[Path] = None
        # Re-entry guard for the logger-driven prompt trigger (replaces the old
        # ReplListener._in_repl). Set while `run()` is active.
        self._in_repl_run = False
        # Extra consumers of the keyword event stream (e.g. a debug controller).
        # The interpreter's own start_keyword/end_keyword hooks stay the primary
        # consumer; observers run alongside them.
        self._observers: List["ExecutionObserver"] = []
        # Unhandled failures of the prompt loop, recorded only while `record_failures`
        # is set (by `robotcode repl`). The `repl` marker keyword fails the session test
        # with them.
        self.record_failures = False
        self.failures: List[ExecutionFailed] = []
        # The code given to `.exit`/`.quit`, None without one.
        self.exit_code: Optional[int] = None

    @property
    def curdir(self) -> Path:
        if self._curdir is None:
            self._curdir = self.source.parent if self.source is not None else Path.cwd()
        return self._curdir

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

    def _parse_test_body(self, command: str) -> Tuple[Any, TestCase]:
        suite_str = (
            "*** Test Cases ***\nDummyTestCase423141592653589793\n  "
            + ("\n  ".join(command.split("\n")) if "\n" in command else command)
        ) + "\n"

        with StringIO(suite_str) as source:
            model = get_model(source, curdir=str(self.curdir).replace("\\", "\\\\"))

        # RF < 6.1 expects a `str` source; RF 6.1+ converts it to a `Path` itself.
        model.source = str(self.source) if self.source is not None else None
        _mark_settings_as_errors(model.sections[0].body[0])

        suite: TestSuite = TestSuite.from_model(model)

        return model, cast(TestCase, suite.tests[0])

    def get_test_body_from_string(self, command: str) -> Tuple[TestCase, List[str]]:
        model, test = self._parse_test_body(command)

        errors: List[str] = []

        for node in iter_nodes(model):
            errors.extend(self.check_for_errors(node))

        return test, errors

    def parse_input(self, text: str) -> ReplInput:
        """Parse REPL input as a test body without raising on errors.

        Unlike `get_test_body_from_string`, whose `SyntaxError` for token errors
        `repl_server` relies on, invalid statements are left to Robot Framework,
        which fails them when execution reaches them.
        """
        model, test = self._parse_test_body(text)

        errors: List[str] = []
        incomplete = False

        for node in iter_nodes(model):
            try:
                errors.extend(self.check_for_errors(node))
            except SyntaxError as e:
                errors.append(str(e))
            if isinstance(node, _END_BLOCKS) and node.header.type in _BLOCK_OPENERS and node.end is None:
                incomplete = True

        return ReplInput(test=test, errors=errors, incomplete=incomplete)

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
            message = f"{type(e)}: {e}"
            self.log_message(message, "ERROR", timestamp=datetime.now())  # noqa: DTZ005
            self._record_failure(ExecutionFailed(message))

    def _record_failure(self, error: ExecutionFailed) -> None:
        if self.record_failures:
            # Split like Robot Framework's body runner does, so the combined message
            # numbers each failure.
            self.failures.extend(error.get_errors())

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
                    self._record_failure(ExecutionFailed(str(e)))
                except ExecutionPassed as e:
                    # Failures continued before `Pass Execution` still fail a test in Robot Framework.
                    if e.earlier_failures:
                        self._record_failure(e.earlier_failures)
                except ExecutionFailed as e:
                    # As in Robot Framework, a skip counts as skipped even when failures
                    # were continued before it.
                    if not e.skip:
                        self._record_failure(e)
                except BaseException as e:
                    self.log_message(str(e), "ERROR", timestamp=datetime.now())  # noqa: DTZ005
                    self._record_failure(ExecutionFailed(str(e)))
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

    def start_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
        pass

    def end_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
        pass

    def start_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
        pass

    def end_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
        pass

    # --- execution-event fan-out + logger-driven prompt trigger -------------

    def register_observer(self, observer: "ExecutionObserver") -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unregister_observer(self, observer: "ExecutionObserver") -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    @contextlib.contextmanager
    def forward_events(self, *, echo_messages: bool = True) -> Iterator[None]:
        """Enable logger→observer forwarding for a run NOT driven by `run()`.

        `run()` flips the logger on itself for the interactive prompt loop; a
        real suite executed by the runner (with a debugger attached) never calls
        `run()`, so observers would see nothing. Wrap that execution in this to
        forward events for its duration. `echo_messages=False` mutes this
        interpreter's own log echoing (the runner's console already shows suite
        output), while still forwarding keyword/test/suite events to observers.
        """
        prev_enabled = self._logger.enabled
        prev_echo = self._logger.echo_messages
        self._logger.enabled = True
        self._logger.echo_messages = echo_messages
        try:
            yield
        finally:
            self._logger.enabled = prev_enabled
            self._logger.echo_messages = prev_echo

    def _notify_start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        self.start_keyword(data, result)
        for observer in self._observers:
            observer.start_keyword(data, result)

    def _notify_end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        for observer in reversed(self._observers):
            observer.end_keyword(data, result)
        self.end_keyword(data, result)

    def _notify_start_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
        self.start_test(data, result)
        for observer in self._observers:
            observer.start_test(data, result)

    def _notify_start_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
        self.start_suite(data, result)
        for observer in self._observers:
            observer.start_suite(data, result)

    def _notify_end_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
        for observer in reversed(self._observers):
            observer.end_test(data, result)
        self.end_test(data, result)

    def _notify_end_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
        for observer in reversed(self._observers):
            observer.end_suite(data, result)
        self.end_suite(data, result)

    def _is_repl_marker(self, result: "result.Keyword") -> bool:
        # The synthetic suite calls the no-op `Repl` keyword from
        # `robotcode.repl.Repl`; its qualified name is the trigger. Control
        # structures have no qualified name (None on RF>=7), so they never match
        # — and the RF>=7-deprecated `result.name` is never read for them.
        return result_qualified_name(result) == "robotcode.repl.Repl.Repl"

    def _maybe_trigger_repl(self, result: "result.Keyword") -> bool:
        """When the `Repl` marker keyword starts, run the interactive prompt.

        Returns True if the trigger fired (the caller should then stop
        processing this event). Re-entry is guarded by `_in_repl_run`. This is
        checked in the logger *before* the `enabled` gate, so it fires even
        though forwarding is still off — replacing the former ReplListener.
        """
        if self._in_repl_run or not self._is_repl_marker(result):
            return False
        global _active_interpreter
        _active_interpreter = self
        self._in_repl_run = True
        try:
            self.run()
        finally:
            self._in_repl_run = False
        return True


TRUE_STRINGS = {"TRUE", "YES", "ON", "1"}


def is_true(value: Union[str, bool]) -> bool:
    if isinstance(value, str):
        return value.upper() in TRUE_STRINGS
    return bool(value)
