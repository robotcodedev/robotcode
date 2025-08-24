import itertools
import os
import pathlib
import re
import reprlib
import threading
import time
import weakref
from collections import OrderedDict, deque
from enum import Enum
from functools import cached_property
from pathlib import Path, PurePath
from typing import (
    Any,
    Callable,
    ClassVar,
    Deque,
    Dict,
    Iterator,
    List,
    Literal,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Union,
    cast,
)

from robot.api.parsing import get_model
from robot.errors import VariableError
from robot.output import LOGGER
from robot.running import EXECUTION_CONTEXTS, Keyword, TestCase, TestSuite
from robot.variables import evaluate_expression

from robotcode.core.event import event
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.utils import get_robot_version

from .dap_types import (
    Breakpoint,
    CompletionItem,
    CompletionItemType,
    ContinuedEvent,
    ContinuedEventBody,
    EvaluateArgumentContext,
    Event,
    ExceptionFilterOptions,
    ExceptionOptions,
    OutputCategory,
    OutputEvent,
    OutputEventBody,
    OutputGroup,
    Scope,
    Source,
    SourceBreakpoint,
    StackFrame,
    StackFrameFormat,
    SteppingGranularity,
    StoppedEvent,
    StoppedEventBody,
    StoppedReason,
    Thread,
    ValueFormat,
    Variable,
    VariablePresentationHint,
)
from .id_manager import IdManager

if get_robot_version() >= (5, 0):
    from robot.running.model import Try
    from robot.utils import Matcher as RobotMatcher

if get_robot_version() >= (7, 0):
    from robot.running import UserKeyword as UserKeywordHandler
else:
    from robot.running.userkeyword import UserKeywordHandler

if get_robot_version() >= (6, 1):

    def internal_evaluate_expression(expression: str, variable_store: Any) -> Any:
        return evaluate_expression(expression, variable_store)

else:

    def internal_evaluate_expression(expression: str, variable_store: Any) -> Any:
        return evaluate_expression(expression, variable_store.store)


class Undefined:
    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "<undefined>"


UNDEFINED = Undefined()


# Debugger configuration constants
STATE_CHANGE_DELAY = 0.01  # Delay to avoid busy loops during state changes
EVALUATE_TIMEOUT = 120  # Timeout for keyword evaluation in seconds
KEYWORD_EVALUATION_TIMEOUT = 60  # Timeout for keyword evaluation wait in seconds
MAX_VARIABLE_ITEMS_DISPLAY = 500  # Maximum items to display in variable view
MAX_REGEX_CACHE_SIZE = 25  # Maximum number of compiled regex patterns to cache


# Type definitions for better type safety
EvaluationResult = Union[Any, Exception]
KeywordCallable = Callable[[], EvaluationResult]
AttributeDict = Dict[str, Any]


class ExceptionInformation(TypedDict, total=False):
    text: Optional[str]
    description: str
    status: str


class LogMessage(TypedDict, total=False):
    level: str
    message: str
    timestamp: str
    html: Optional[str]


class RobotContextProtocol(Protocol):
    """Protocol for Robot Framework execution context."""

    variables: Any
    namespace: Any


class KeywordHandlerProtocol(Protocol):
    """Protocol for Robot Framework keyword handlers."""

    name: str
    args: Any  # Robot version dependent type
    arguments: Any  # Robot version dependent type


class DebugRepr(reprlib.Repr):
    def __init__(self) -> None:
        super().__init__()
        self.maxtuple = 50
        self.maxlist = 50
        self.maxarray = 50
        self.maxdict = 500
        self.maxset = 50
        self.maxfrozenset = 50
        self.maxdeque = 50
        self.maxstring = 500


class EvaluateResult(NamedTuple):
    result: str
    type: Optional[str] = None
    presentation_hint: Optional[VariablePresentationHint] = None
    variables_reference: int = 0
    named_variables: Optional[int] = None
    indexed_variables: Optional[int] = None
    memory_reference: Optional[str] = None


class SetVariableResult(NamedTuple):
    value: str
    type: Optional[str]
    variables_reference: Optional[int] = None
    named_variables: Optional[int] = None
    indexed_variables: Optional[int] = None


class State(Enum):
    Stopped = 0
    Running = 1
    Paused = 2
    CallKeyword = 3


class RequestedState(Enum):
    Nothing = 0
    Pause = 1
    Next = 2
    StepIn = 3
    StepOut = 4
    Running = 5


class BreakpointsEntry(NamedTuple):
    breakpoints: Tuple[SourceBreakpoint, ...]
    lines: Tuple[int, ...]


class ExceptionBreakpointsEntry(NamedTuple):
    filters: Tuple[str, ...]
    filter_options: Optional[Tuple[ExceptionFilterOptions, ...]] = None
    exception_options: Optional[Tuple[ExceptionOptions, ...]] = None


class StackTraceResult(NamedTuple):
    stack_frames: List[StackFrame]
    total_frames: int


class InvalidThreadIdError(Exception):
    def __init__(self, current_thread_id: Any, expected_thread_id: Any = None) -> None:
        super().__init__(
            f"Invalid thread id {current_thread_id}"
            + (f", expected {expected_thread_id}" if expected_thread_id is not None else "")
        )


class MarkerObject:
    pass


class StackFrameEntry:
    def __init__(
        self,
        parent: Optional["StackFrameEntry"],
        context: Any,
        name: str,
        type: str,
        source: Optional[str],
        line: Optional[int],
        column: Optional[int] = None,
        handler: Optional[UserKeywordHandler] = None,
        is_file: bool = True,
        libname: Optional[str] = None,
        kwname: Optional[str] = None,
        longname: Optional[str] = None,
    ) -> None:
        self.parent = weakref.ref(parent) if parent is not None else None
        self.context = weakref.ref(context)
        self.variables = weakref.ref(context.variables.current)
        self.name = name
        self.type = type
        self.source = source
        self.line = line
        self.column = column
        self.handler = handler
        self.is_file = is_file
        self.top_hidden = False
        self.libname = libname
        self.kwname = kwname
        self.longname = longname
        self._suite_marker = MarkerObject()
        self._test_marker = MarkerObject()
        self._local_marker = MarkerObject()
        self._global_marker = MarkerObject()
        self.stack_frames: Deque[StackFrameEntry] = deque()

    def __repr__(self) -> str:
        return f"StackFrameEntry({self.name!r}, {self.type!r}, {self.source!r}, {self.line!r}, {self.column!r})"

    def get_first_or_self(self) -> "StackFrameEntry":
        if self.stack_frames:
            return self.stack_frames[0]
        return self

    _id_manager = IdManager()

    @cached_property
    def id(self) -> int:
        return self._id_manager.get_id(self)

    @cached_property
    def test_id(self) -> int:
        return self._id_manager.get_id(self._test_marker)

    @cached_property
    def suite_id(self) -> int:
        return self._id_manager.get_id(self._suite_marker)

    @cached_property
    def local_id(self) -> int:
        return self._id_manager.get_id(self._local_marker)

    @cached_property
    def global_id(self) -> int:
        return self._id_manager.get_id(self._global_marker)


class HitCountEntry(NamedTuple):
    source: pathlib.PurePath
    line: int
    type: str


class PathMapping(NamedTuple):
    local_root: Optional[str]
    remote_root: Optional[str]


class DebugLoggerBase:
    def __init__(self) -> None:
        self.steps: List[Any] = []


if get_robot_version() < (7, 0):

    class DebugLogger(DebugLoggerBase):
        def start_keyword(self, kw: Any) -> None:
            self.steps.append(kw)

        def end_keyword(self, kw: Any) -> None:
            self.steps.pop()

else:
    from robot import result, running
    from robot.output.loggerapi import LoggerApi

    class DebugLogger(DebugLoggerBase, LoggerApi):  # type: ignore[no-redef]
        def start_try(self, data: "running.Try", result: "result.Try") -> None:
            self.steps.append(data)

        def end_try(self, data: "running.Try", result: "result.Try") -> None:
            self.steps.pop()

        def start_keyword(self, data: running.Keyword, result: result.Keyword) -> None:
            self.steps.append(data)

        def end_keyword(self, data: running.Keyword, result: result.Keyword) -> None:
            self.steps.pop()


breakpoint_id_manager = IdManager()


class _DebuggerInstanceDescriptor:
    """Descriptor that forwards all attribute access to the singleton instance."""

    def __init__(self) -> None:
        self._owner_class: Optional[type] = None

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when the descriptor is assigned to a class."""
        self._owner_class = owner

    def __get__(self, obj: Any, owner: Optional[type]) -> "Debugger":
        if self._owner_class is None:
            self._owner_class = owner
        if self._owner_class is not None and hasattr(self._owner_class, "_get_instance"):
            return cast("Debugger", self._owner_class._get_instance())
        # This should never happen in practice, but needed for type checking
        raise RuntimeError("Debugger class not properly initialized")

    def __set__(self, obj: Any, value: Any) -> None:
        raise AttributeError("Cannot replace the debugger instance")

    def __delete__(self, obj: Any) -> None:
        raise AttributeError("Cannot delete the debugger instance")


class Debugger:
    __instance: ClassVar[Optional["Debugger"]] = None
    __lock: ClassVar = threading.RLock()
    __inside_instance: ClassVar = False

    _logger = LoggingDescriptor()

    # Descriptor that allows Debugger.instance.field = value syntax
    instance = _DebuggerInstanceDescriptor()

    @classmethod
    def _get_instance(cls) -> "Debugger":
        """Internal method to get the singleton instance."""
        if cls.__instance is not None:
            return cls.__instance
        with cls.__lock:
            if cls.__instance is None:
                cls.__inside_instance = True
                try:
                    cls.__instance = cls()
                finally:
                    cls.__inside_instance = False
        return cls.__instance

    @classmethod
    def get_instance(cls) -> "Debugger":
        """Backward compatibility method for old instance() calls."""
        return cls._get_instance()

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None and cls.__inside_instance:
                    return super().__new__(cls)

        raise RuntimeError(f"Attempt to create a '{cls.__qualname__}' instance outside of instance()")

    def __init__(self) -> None:
        self.breakpoints: Dict[pathlib.PurePath, BreakpointsEntry] = {}

        self.exception_breakpoints: Set[ExceptionBreakpointsEntry] = set()
        self.exception_breakpoints.add(
            ExceptionBreakpointsEntry((), (ExceptionFilterOptions("uncaught_failed_keyword"),), ())
        )

        self.main_thread: Optional[threading.Thread] = None
        self.full_stack_frames: Deque[StackFrameEntry] = deque()
        self.stack_frames: Deque[StackFrameEntry] = deque()
        self.condition = threading.Condition()
        self._state: State = State.Stopped
        self.requested_state: RequestedState = RequestedState.Nothing
        self.stop_stack_len = 0
        self._robot_report_file: Optional[str] = None
        self._robot_log_file: Optional[str] = None
        self._robot_output_file: Optional[str] = None
        self.output_messages: bool = False
        self.output_log: bool = False
        self.output_timestamps: bool = False
        self.colored_output: bool = True
        self.group_output: bool = False
        self.hit_counts: Dict[HitCountEntry, int] = {}
        self.last_fail_message: Optional[str] = None
        self.stop_on_entry = False
        self._debug = True
        self.terminated = False
        self.attached = False
        self.path_mappings: List[PathMapping] = []

        self._keyword_to_evaluate: Optional[KeywordCallable] = None
        self._evaluated_keyword_result: Optional[EvaluationResult] = None
        self._evaluate_keyword_event = threading.Event()
        self._evaluate_keyword_event.set()
        self._after_evaluate_keyword_event = threading.Event()
        self._after_evaluate_keyword_event.set()
        self.expression_mode = False

        self.debug_logger: Optional[DebugLogger] = None
        self.run_started = False
        self._variables_cache: Dict[int, Any] = {}
        self._variables_object_cache: List[Any] = []
        self._current_exception: Optional[ExceptionInformation] = None

    @property
    def state(self) -> State:
        return self._state

    @state.setter
    def state(self, value: State) -> None:
        # if state is changed, do nothing and wait a little bit to avoid busy loop

        if self._state == State.Paused and value not in [
            State.Paused,
            State.CallKeyword,
        ]:
            self._clear_all_caches()

        time.sleep(STATE_CHANGE_DELAY)

        self._state = value

    @property
    def debug(self) -> bool:
        return self._debug

    @debug.setter
    def debug(self, value: bool) -> None:
        self._debug = value

    @property
    def robot_report_file(self) -> Optional[str]:
        return self._robot_report_file

    @robot_report_file.setter
    def robot_report_file(self, value: Optional[str]) -> None:
        self._robot_report_file = value

    @property
    def robot_log_file(self) -> Optional[str]:
        return self._robot_log_file

    @robot_log_file.setter
    def robot_log_file(self, value: Optional[str]) -> None:
        self._robot_log_file = value

    @property
    def robot_output_file(self) -> Optional[str]:
        return self._robot_output_file

    @robot_output_file.setter
    def robot_output_file(self, value: Optional[str]) -> None:
        self._robot_output_file = value

    def terminate(self) -> None:
        self.terminated = True

    def _clear_all_caches(self) -> None:
        """Optimized method to clear all caches in one operation."""
        self._variables_cache.clear()
        self._variables_object_cache.clear()
        self.__compiled_regex_cache.clear()

    def start(self) -> None:
        with self.condition:
            self.state = State.Running
            self.condition.notify_all()

    def stop(self) -> None:
        with self.condition:
            self.state = State.Stopped

            if self.main_thread_is_alive:
                self.send_event(
                    self,
                    ContinuedEvent(
                        body=ContinuedEventBody(
                            thread_id=self.main_thread_id,
                            all_threads_continued=True,
                        )
                    ),
                )

            self.condition.notify_all()

    def check_thread_id(self, thread_id: int) -> None:
        if not self.main_thread_is_alive and thread_id != self.main_thread_id:
            raise InvalidThreadIdError(thread_id, self.main_thread_id)

    def continue_all_if_paused(self) -> None:
        if self.state == State.Paused:
            self.continue_all()

    def continue_all(self) -> None:
        if self.main_thread_is_alive:
            self.continue_thread(self.main_thread_id)

    def continue_thread(self, thread_id: int) -> None:
        self.check_thread_id(thread_id)

        with self.condition:
            self.requested_state = RequestedState.Running
            self.condition.notify_all()

    def pause_thread(self, thread_id: int) -> None:
        if thread_id != 0:
            self.check_thread_id(thread_id)

        with self.condition:
            self.requested_state = RequestedState.Pause

            self.condition.notify_all()

    def next(self, thread_id: int, granularity: Optional[SteppingGranularity] = None) -> None:
        self.check_thread_id(thread_id)

        with self.condition:
            if self.full_stack_frames and self.full_stack_frames[0].type in [
                "TEST",
                "SUITE",
            ]:
                self.requested_state = RequestedState.StepIn
            else:
                self.requested_state = RequestedState.Next

                self.stop_stack_len = len(self.full_stack_frames)
                if self.full_stack_frames and self.full_stack_frames[0].type in [
                    "FOR",
                    "FOR ITERATION",
                    "ITERATION",
                    "IF",
                    "ELSE",
                    "ELSE IF",
                    "TRY",
                    "EXCEPT",
                    "FINALLY",
                    "WHILE",
                ]:
                    self.stop_stack_len += 1

            self.condition.notify_all()

    def step_in(
        self,
        thread_id: int,
        target_id: Optional[int] = None,
        granularity: Optional[SteppingGranularity] = None,
    ) -> None:
        self.check_thread_id(thread_id)

        with self.condition:
            self.requested_state = RequestedState.StepIn

            self.condition.notify_all()

    def step_out(self, thread_id: int, granularity: Optional[SteppingGranularity] = None) -> None:
        self.check_thread_id(thread_id)

        with self.condition:
            self.requested_state = RequestedState.StepOut
            self.stop_stack_len = len(self.full_stack_frames) - 1

            i = 1

            while i < len(self.full_stack_frames) and self.full_stack_frames[i].type in [
                "FOR",
                "FOR ITERATION",
                "ITERATION",
                "IF",
                "ELSE",
                "ELSE IF",
                "TRY",
                "EXCEPT",
                "FINALLY",
                "WHILE",
            ]:
                self.stop_stack_len -= 1
                i += 1

            self.condition.notify_all()

    @event
    def send_event(sender: Any, event: Event) -> None: ...

    def set_breakpoints(
        self,
        source: Source,
        breakpoints: Optional[List[SourceBreakpoint]] = None,
        lines: Optional[List[int]] = None,
        source_modified: Optional[bool] = None,
    ) -> List[Breakpoint]:
        if self.is_windows_path(source.path or ""):
            path: pathlib.PurePath = pathlib.PureWindowsPath(source.path or "")
        else:
            path = pathlib.PurePath(source.path or "")

        if path in self.breakpoints and not breakpoints and not lines:
            self.breakpoints.pop(path)
        elif path:
            self.breakpoints[path] = result = BreakpointsEntry(
                tuple(breakpoints) if breakpoints else (),
                tuple(lines) if lines else (),
            )
            return [
                Breakpoint(
                    id=breakpoint_id_manager.get_id(v),
                    source=Source(path=str(path)),
                    verified=True,
                    line=v.line,
                )
                for v in result.breakpoints
            ]

        self._logger.error("not supported breakpoint")

        return []

    def process_start_state(self, source: str, line_no: int, type: str, status: str) -> None:
        if self.state == State.CallKeyword:
            return

        if self.state == State.Stopped:
            return

        if self.requested_state == RequestedState.Pause:
            self.requested_state = RequestedState.Nothing
            self.state = State.Paused

            self.send_event(
                self,
                StoppedEvent(
                    body=StoppedEventBody(
                        description="Paused",
                        reason=StoppedReason.PAUSE,
                        thread_id=self.main_thread_id,
                    )
                ),
            )

        elif self.requested_state == RequestedState.Next:
            if len(self.full_stack_frames) <= self.stop_stack_len:
                self.requested_state = RequestedState.Nothing
                self.state = State.Paused

                self.send_event(
                    self,
                    StoppedEvent(
                        body=StoppedEventBody(
                            description="Next step",
                            reason=StoppedReason.STEP,
                            thread_id=self.main_thread_id,
                        )
                    ),
                )

        elif self.requested_state == RequestedState.StepIn:
            self.requested_state = RequestedState.Nothing
            self.state = State.Paused

            self.send_event(
                self,
                StoppedEvent(
                    body=StoppedEventBody(
                        description="Step in",
                        reason=StoppedReason.STEP,
                        thread_id=self.main_thread_id,
                    )
                ),
            )

        elif self.requested_state == RequestedState.StepOut and len(self.full_stack_frames) <= self.stop_stack_len:
            self.requested_state = RequestedState.Nothing
            self.state = State.Paused

            self.send_event(
                self,
                StoppedEvent(
                    body=StoppedEventBody(
                        description="Step out",
                        reason=StoppedReason.STEP,
                        thread_id=self.main_thread_id,
                    )
                ),
            )

        if source is not None:
            source_path = self.map_path_to_client(str(Path(source).absolute()))
            if source_path in self.breakpoints:
                breakpoints = [v for v in self.breakpoints[source_path].breakpoints if v.line == line_no]
                if len(breakpoints) > 0:
                    for point in breakpoints:
                        if point.condition is not None:
                            hit = False
                            try:
                                vars = EXECUTION_CONTEXTS.current.variables.current
                                hit = bool(
                                    internal_evaluate_expression(
                                        vars.replace_string(point.condition),
                                        vars,
                                    )
                                )
                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException:
                                hit = False

                            if not hit:
                                return
                        if point.hit_condition is not None:
                            hit = False
                            entry = HitCountEntry(source_path, line_no, type)
                            if entry not in self.hit_counts:
                                self.hit_counts[entry] = 0
                            self.hit_counts[entry] += 1
                            try:
                                hit = self.hit_counts[entry] != int(point.hit_condition)
                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException:
                                hit = False
                            if not hit:
                                return
                        if point.log_message:
                            vars = EXECUTION_CONTEXTS.current.variables.current
                            try:
                                message = vars.replace_string(point.log_message)
                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException as e:
                                message = f"{point.log_message}\nError: {e}"
                            self.send_event(
                                self,
                                OutputEvent(
                                    body=OutputEventBody(
                                        output=message + os.linesep,
                                        category=OutputCategory.CONSOLE,
                                        source=Source(path=str(source_path)),
                                        line=line_no,
                                    )
                                ),
                            )
                            return

                        self.requested_state = RequestedState.Nothing
                        self.state = State.Paused

                        self.send_event(
                            self,
                            StoppedEvent(
                                body=StoppedEventBody(
                                    description="Breakpoint hit",
                                    reason=StoppedReason.BREAKPOINT,
                                    thread_id=self.main_thread_id,
                                    hit_breakpoint_ids=[breakpoint_id_manager.get_id(v) for v in breakpoints],
                                )
                            ),
                        )

    def process_end_state(
        self,
        status: str,
        filter_id: Set[str],
        description: str,
        text: Optional[str],
    ) -> None:
        if self.state == State.CallKeyword:
            return
        if self.state == State.Stopped:
            return

        if (
            not self.terminated
            and status == "FAIL"
            and any(
                v
                for v in self.exception_breakpoints
                if v.filter_options and any(o for o in v.filter_options if o.filter_id in filter_id)
            )
        ):
            reason = StoppedReason.EXCEPTION

            self.requested_state = RequestedState.Nothing
            self.state = State.Paused

            self._current_exception = {"text": text, "description": description, "status": status}

            self.send_event(
                self,
                StoppedEvent(
                    body=StoppedEventBody(
                        reason=reason,
                        thread_id=self.main_thread_id,
                        description=description,
                        text=text,
                    )
                ),
            )

    def wait_for_running(self) -> None:
        if self.attached:
            while True:
                with self.condition:
                    self.condition.wait_for(
                        lambda: self.state in [State.Running, State.Stopped, State.CallKeyword]
                        or self.requested_state != RequestedState.Nothing
                    )

                if self.state == State.CallKeyword:
                    self._evaluated_keyword_result = None
                    try:
                        if self._keyword_to_evaluate is not None:
                            self._evaluated_keyword_result = self._keyword_to_evaluate()
                            self._keyword_to_evaluate = None
                    except (SystemExit, KeyboardInterrupt):
                        raise
                    except BaseException as e:
                        self._evaluated_keyword_result = e
                    finally:
                        self._evaluate_keyword_event.set()
                        self._after_evaluate_keyword_event.wait(EVALUATE_TIMEOUT)

                    continue

                if self.requested_state == RequestedState.Running:
                    self.requested_state = RequestedState.Nothing
                    self.state = State.Running
                    if self.main_thread_is_alive:
                        self.send_event(
                            self,
                            ContinuedEvent(
                                body=ContinuedEventBody(
                                    thread_id=self.main_thread_id,
                                    all_threads_continued=True,
                                )
                            ),
                        )
                    continue

                break
            self._current_exception = None

    def start_output_group(self, name: str, attributes: AttributeDict, type: Optional[str] = None) -> None:
        if self.group_output:
            source = attributes.get("source")
            line_no = attributes.get("lineno")

            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output=f"\u001b[38;5;14m{(type + ' ') if type else ''}\u001b[0m{name}\n",
                        category="OutputCategory.CONSOLE",
                        group=OutputGroup.START,
                        source=Source(path=str(self.map_path_to_client(source))) if source else None,
                        line=line_no if source is not None else None,
                        column=0 if source is not None else None,
                    )
                ),
            )

    def end_output_group(self, name: str, attributes: AttributeDict, type: Optional[str] = None) -> None:
        if self.group_output:
            source = attributes.get("source")
            line_no = attributes.get("lineno")

            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output="",
                        category=OutputCategory.CONSOLE,
                        group=OutputGroup.END,
                        source=Source(path=str(self.map_path_to_client(source))) if source else None,
                        line=line_no if source is not None else None,
                        column=0 if source is not None else None,
                    )
                ),
            )

    def add_stackframe_entry(
        self,
        name: str,
        type: str,
        source: Optional[str],
        line: Optional[int],
        column: Optional[int] = None,
        *,
        handler: Optional[KeywordHandlerProtocol] = None,
        libname: Optional[str] = None,
        kwname: Optional[str] = None,
        longname: Optional[str] = None,
    ) -> StackFrameEntry:
        path = pathlib.Path(source) if source is not None else None
        is_file = path is not None and path.is_file()
        if path is not None and not is_file and type in ["SETUP", "TEARDOWN"]:
            init_path = pathlib.Path(path, "__init__.robot")
            if init_path.exists() and init_path.is_file():
                is_file = True
                source = str(init_path)

        result = StackFrameEntry(
            self.stack_frames[0] if self.stack_frames else None,
            EXECUTION_CONTEXTS.current,
            name,
            type,
            source,
            line,
            column,
            handler=handler,
            is_file=is_file,
            libname=libname,
            kwname=kwname,
            longname=longname,
        )

        self.full_stack_frames.appendleft(result)

        if type == "KEYWORD" and source is None and line is None and column is None:
            return result

        if type in ["SUITE", "TEST"]:
            self.stack_frames.appendleft(result)
        elif type in ["KEYWORD", "SETUP", "TEARDOWN"] and isinstance(handler, UserKeywordHandler):
            result.top_hidden = True
            if self.stack_frames:
                self.stack_frames[0].stack_frames.appendleft(result)
            self.stack_frames.appendleft(result)
        else:
            if self.stack_frames:
                self.stack_frames[0].stack_frames.appendleft(result)

        return result

    def remove_stackframe_entry(
        self,
        name: str,
        type: str,
        source: Optional[str],
        line: Optional[int],
        column: Optional[int] = None,
        *,
        handler: Optional[KeywordHandlerProtocol] = None,
    ) -> None:
        self.full_stack_frames.popleft()

        if type == "KEYWORD" and source is None and line is None and column is None:
            return

        if type in ["SUITE", "TEST"]:
            self.stack_frames.popleft()
        elif type in ["KEYWORD", "SETUP", "TEARDOWN"] and isinstance(handler, UserKeywordHandler):
            self.stack_frames.popleft()

            if self.stack_frames:
                self.stack_frames[0].stack_frames.popleft()
        else:
            if self.stack_frames:
                self.stack_frames[0].stack_frames.popleft()

    def start_suite(self, name: str, attributes: AttributeDict) -> None:
        if self.state == State.CallKeyword:
            return

        if not self.run_started:
            self.run_started = True
            self.debug_logger = DebugLogger()
            LOGGER.register_logger(self.debug_logger)

        source = attributes.get("source")
        line_no_dummy = attributes.get("lineno", 1)
        if isinstance(line_no_dummy, str):
            line_no = int(line_no_dummy) if line_no_dummy else None
        else:
            line_no = line_no_dummy
        longname = attributes.get("longname", "")
        status = attributes.get("status", "")
        type = "SUITE"

        entry = self.add_stackframe_entry(name, type, source, line_no, longname=longname)

        if self.debug:
            if self.stop_on_entry:
                self.stop_on_entry = False

                self.requested_state = RequestedState.Nothing
                self.state = State.Paused
                self.send_event(
                    self,
                    StoppedEvent(
                        body=StoppedEventBody(
                            reason=StoppedReason.ENTRY,
                            thread_id=self.main_thread_id,
                        )
                    ),
                )

                self.wait_for_running()
            elif entry.source:
                self.process_start_state(
                    entry.source,
                    entry.line if entry.line is not None else 0,
                    entry.type,
                    status,
                )

                self.wait_for_running()

    def end_suite(self, name: str, attributes: AttributeDict) -> None:
        if self.state == State.CallKeyword:
            return

        if self.debug:
            status = attributes.get("status", "")

            if status == "FAIL":
                self.process_end_state(
                    status,
                    {"failed_suite"},
                    "Suite failed.",
                    f"Suite failed{f': {v}' if (v := attributes.get('message')) else ''}",
                )
                self.wait_for_running()

        source = attributes.get("source")
        line_no = attributes.get("lineno", 1)
        type = "SUITE"

        self.remove_stackframe_entry(name, type, source, line_no)

    def start_test(self, name: str, attributes: AttributeDict) -> None:
        if self.state == State.CallKeyword:
            return

        source = attributes.get("source")
        line_no_dummy = attributes.get("lineno", 1)
        if isinstance(line_no_dummy, str):
            line_no = int(line_no_dummy) if line_no_dummy else None
        else:
            line_no = line_no_dummy
        longname = attributes.get("longname", "")
        status = attributes.get("status", "")

        type = "TEST"

        entry = self.add_stackframe_entry(name, type, source, line_no, longname=longname)

        if self.debug and entry.source:
            self.process_start_state(
                entry.source,
                entry.line if entry.line is not None else 0,
                entry.type,
                status,
            )

            self.wait_for_running()

    def end_test(self, name: str, attributes: AttributeDict) -> None:
        if self.state == State.CallKeyword:
            return

        if self.debug:
            status = attributes.get("status", "")

            if status == "FAIL":
                self.process_end_state(
                    status,
                    {""},
                    "Test failed.",
                    f"Test failed{f': {v}' if (v := attributes.get('message')) else ''}",
                )

                self.wait_for_running()

        source = attributes.get("source")
        line_no = attributes.get("lineno", 1)
        longname = attributes.get("longname", "")
        type = "TEST"

        self.remove_stackframe_entry(longname, type, source, line_no)

    if get_robot_version() >= (7, 0):

        def get_current_keyword_handler(self, name: str) -> UserKeywordHandler:
            return EXECUTION_CONTEXTS.current.namespace.get_runner(name).keyword

    else:

        def get_current_keyword_handler(self, name: str) -> UserKeywordHandler:
            return EXECUTION_CONTEXTS.current.namespace.get_runner(name)._handler

    def start_keyword(self, name: str, attributes: AttributeDict) -> None:
        if self.state == State.CallKeyword:
            return

        status = attributes.get("status", "")
        source = attributes.get("source")
        line_no_dummy = attributes.get("lineno", 1)
        if isinstance(line_no_dummy, str):
            line_no = int(line_no_dummy) if line_no_dummy else None
        else:
            line_no = line_no_dummy
        type = attributes.get("type", "KEYWORD")
        libname = attributes.get("libname")
        kwname = attributes.get("kwname")

        handler: Optional[KeywordHandlerProtocol] = None
        if type in ["KEYWORD", "SETUP", "TEARDOWN"]:
            try:
                handler = self.get_current_keyword_handler(name)
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass

        entry = self.add_stackframe_entry(
            str(kwname),
            type,
            source,
            line_no,
            handler=handler,
            libname=libname,
            kwname=kwname,
            longname=name,
        )

        if status == "NOT RUN" and type != "IF":
            return

        if self.debug and entry.source and entry.line is not None:
            self.process_start_state(entry.source, entry.line, entry.type, status)

            self.wait_for_running()

    CAUGHTED_KEYWORDS: ClassVar[List[str]] = [
        "BuiltIn.Run Keyword And Expect Error",
        "BuiltIn.Run Keyword And Ignore Error",
        "BuiltIn.Run Keyword And Warn On Failure",
        "BuiltIn.Wait Until Keyword Succeeds",
        "BuiltIn.Run Keyword And Continue On Failure",
        "BuiltIn.Run Keyword And Return Status",
    ]

    def is_not_caughted_by_keyword(self) -> bool:
        r = next(
            (
                v
                for v in itertools.islice(self.full_stack_frames, 1, None)
                if v.type == "KEYWORD" and v.longname in self.CAUGHTED_KEYWORDS
            ),
            None,
        )
        return r is None

    __matchers: Optional[Dict[str, Callable[[str, str], bool]]] = None
    __compiled_regex_cache: "OrderedDict[str, re.Pattern[str]]" = OrderedDict()
    __robot_matcher: Optional[Any] = None

    def _get_matcher(self, pattern_type: str) -> Optional[Callable[[str, str], bool]]:
        if self.__matchers is None:
            self.__matchers: Dict[str, Callable[[str, str], bool]] = {
                "GLOB": self._glob_matcher,
                "LITERAL": lambda m, p: m == p,
                "REGEXP": self._regexp_matcher,
                "START": lambda m, p: m.startswith(p),
            }

        return self.__matchers.get(pattern_type.upper(), None)

    def _glob_matcher(self, message: str, pattern: str) -> bool:
        """Optimized glob matcher with cached Robot Matcher."""

        return bool(RobotMatcher(pattern, spaceless=False, caseless=False).match(message))

    def _regexp_matcher(self, message: str, pattern: str) -> bool:
        """Optimized regex matcher with LRU caching (max 25 entries)."""
        if pattern in self.__compiled_regex_cache:
            self.__compiled_regex_cache.move_to_end(pattern)
            compiled_pattern = self.__compiled_regex_cache[pattern]
        else:
            if len(self.__compiled_regex_cache) >= MAX_REGEX_CACHE_SIZE:
                self.__compiled_regex_cache.popitem(last=False)

            try:
                compiled_pattern = re.compile(rf"{pattern}\Z")
                self.__compiled_regex_cache[pattern] = compiled_pattern
            except re.error:
                return False

        return compiled_pattern.match(message) is not None

    def _should_run_except(self, branch: Any, error: str) -> bool:
        if not branch.patterns:
            return True

        if branch.pattern_type:
            pattern_type = EXECUTION_CONTEXTS.current.variables.replace_string(branch.pattern_type)
        else:
            pattern_type = "LITERAL"

        matcher = self._get_matcher(pattern_type)

        if not matcher:
            return False

        for pattern in branch.patterns:
            if matcher(
                error,
                EXECUTION_CONTEXTS.current.variables.replace_string(pattern),
            ):
                return True

        return False

    if get_robot_version() >= (7, 0):

        def _get_step_data(self, step: Any) -> Any:
            return step

    else:

        def _get_step_data(self, step: Any) -> Any:
            return step.data

    if get_robot_version() < (5, 0):

        def is_not_caugthed_by_except(self, message: Optional[str]) -> bool:
            if not message:
                return True
            return False
    else:

        def is_not_caugthed_by_except(self, message: Optional[str]) -> bool:
            if not message:
                return True

            # TODO resolve variables in exception message

            if self.debug_logger:
                if self.debug_logger.steps:
                    for branch in [
                        self._get_step_data(f)
                        for f in reversed(self.debug_logger.steps)
                        if isinstance(self._get_step_data(f), Try)
                    ]:
                        for except_branch in branch.except_branches:
                            if self._should_run_except(except_branch, message):
                                return False
            return True

    def end_keyword(self, name: str, attributes: AttributeDict) -> None:
        if self.state == State.CallKeyword:
            return

        type = attributes.get("type")
        if self.debug:
            status = attributes.get("status", "")

            if status == "FAIL" and type in ["KEYWORD", "SETUP", "TEARDOWN"]:
                self.process_end_state(
                    status,
                    {
                        "failed_keyword",
                        *(
                            {"uncaught_failed_keyword"}
                            if self.is_not_caughted_by_keyword()
                            and self.is_not_caugthed_by_except(self.last_fail_message)
                            else []
                        ),
                    },
                    "Keyword failed.",
                    f"Keyword failed: {self.last_fail_message}" if self.last_fail_message else "Keyword failed.",
                )

                self.wait_for_running()

        source = attributes.get("source")
        line_no = attributes.get("lineno")
        type = attributes.get("type", "KEYWORD")
        kwname = attributes.get("kwname")

        handler: Optional[KeywordHandlerProtocol] = None
        if type in ["KEYWORD", "SETUP", "TEARDOWN"]:
            try:
                handler = self.get_current_keyword_handler(name)
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass

        self.remove_stackframe_entry(str(kwname), type, source, line_no, handler=handler)

    def set_main_thread(self, thread: threading.Thread) -> None:
        self.main_thread = thread

    @property
    def main_thread_id(self) -> int:
        return 1 if self.main_thread_is_alive else 0

    @property
    def main_thread_is_alive(self) -> bool:
        return self.main_thread is not None and self.main_thread.is_alive()

    def get_threads(self) -> List[Thread]:
        return (
            [
                Thread(
                    id=self.main_thread_id,
                    name="RobotMain",
                )
            ]
            if self.main_thread_is_alive
            else []
        )

    WINDOW_PATH_REGEX: ClassVar = re.compile(r"^(([a-z]:[\\/])|(\\\\)).*$", re.RegexFlag.IGNORECASE)

    @classmethod
    def is_windows_path(cls, path: Union["os.PathLike[str]", str]) -> bool:
        return bool(cls.WINDOW_PATH_REGEX.fullmatch(str(path)))

    @staticmethod
    def relative_to(path: pathlib.PurePath, *other: pathlib.PurePath) -> Optional[pathlib.PurePath]:
        try:
            return path.relative_to(*other)
        except ValueError:
            return None

    def map_path_to_client(self, path: Union["os.PathLike[str]", str]) -> pathlib.PurePath:
        if not isinstance(path, PurePath):
            path = PurePath(path)

        if not self.path_mappings:
            return path

        for mapping in self.path_mappings:
            remote_root_path = Path(mapping.remote_root or ".").absolute()

            if (
                mapping.local_root is not None
                and (relative_path := self.relative_to(Path(path), remote_root_path)) is not None
            ):
                if self.is_windows_path(mapping.local_root):
                    return pathlib.PureWindowsPath(mapping.local_root, relative_path)

                return pathlib.PurePath(mapping.local_root, relative_path)

        return path

    def source_from_entry(self, entry: StackFrameEntry) -> Optional[Source]:
        if entry.source is not None and entry.is_file:
            return Source(
                path=str(self.map_path_to_client(entry.source)),
                presentation_hint="normal",
            )

        return None

    def get_stack_trace(
        self,
        thread_id: int,
        start_frame: Optional[int] = None,
        levels: Optional[int] = None,
        format: Optional[StackFrameFormat] = None,
    ) -> StackTraceResult:
        self.check_thread_id(thread_id)

        start_frame = start_frame or 0
        levels = start_frame + (levels or len(self.stack_frames))

        def yield_stack() -> Iterator[StackFrame]:
            for i, v in enumerate(itertools.islice(self.stack_frames, start_frame, levels)):
                if v.stack_frames:
                    yield StackFrame(
                        id=v.id,
                        name=v.longname or v.kwname or v.name or v.type,
                        line=v.stack_frames[0].line if v.stack_frames[0].line is not None else 0,
                        column=v.stack_frames[0].column if v.stack_frames[0].column is not None else 1,
                        source=self.source_from_entry(v.stack_frames[0]),
                        presentation_hint="normal" if v.stack_frames[0].is_file else "subtle",
                        module_id=v.libname,
                    )
                if not v.top_hidden:
                    yield StackFrame(
                        id=v.id,
                        name=v.longname or v.kwname or v.name or v.type,
                        line=v.line if v.line is not None else 1,
                        column=v.column if v.column is not None else 1,
                        source=self.source_from_entry(v),
                        presentation_hint="normal" if v.is_file else "subtle",
                        module_id=v.libname,
                    )

        frames = list(yield_stack())

        return StackTraceResult(frames, len(self.stack_frames))

    MESSAGE_COLORS: ClassVar[Dict[str, str]] = {
        "INFO": "\u001b[38;5;2m",
        "WARN": "\u001b[38;5;3m",
        "ERROR": "\u001b[38;5;1m",
        "TRACE": "\u001b[38;5;4m",
        "FAIL": "\u001b[38;5;5m\u001b[1m",
        "DEBUG": "\u001b[38;5;8m",
    }

    def log_message(self, message: LogMessage) -> None:
        level = message["level"]
        msg = message["message"]

        if level == "FAIL":
            self.last_fail_message = msg

        if self.output_log:
            self._send_log_event(message["timestamp"], level, msg, OutputCategory.CONSOLE)

    RE_FILE_LINE_MATCHER = re.compile(r".+\sin\sfile\s'(?P<file>.*)'\son\sline\s(?P<line>\d+):.*")

    def _send_log_event(
        self,
        timestamp: str,
        level: str,
        msg: str,
        category: Union[OutputCategory, str],
    ) -> None:
        current_frame = self.full_stack_frames[0] if self.full_stack_frames else None
        source = (
            Source(path=str(self.map_path_to_client(current_frame.source)))
            if current_frame and current_frame.is_file and current_frame.source
            else None
        )

        line = current_frame.line if current_frame else None

        match = self.RE_FILE_LINE_MATCHER.match(msg)
        if match:
            source = Source(path=str(self.map_path_to_client(match.group("file"))))
            line = int(match.group("line"))

        self.send_event(
            self,
            OutputEvent(
                body=OutputEventBody(
                    output=self._build_output(level, msg, timestamp),
                    category=category,
                    source=source,
                    line=line if line is not None else 0,
                    column=0 if source is not None else None,
                )
            ),
        )

    def _build_output(self, level: str, msg: str, timestamp: str) -> str:
        if self.colored_output:
            return (
                (f"\u001b[38;5;243m{timestamp.split(' ', 1)[1]}\u001b[0m " if self.output_timestamps else "")
                + (f"[ {self.MESSAGE_COLORS.get(level, '')}{level}\u001b[0m ] " if level != "INFO" else "")
                + f"{msg}\n"
            )

        return (
            (f"{timestamp.split(' ', 1)[1]} " if self.output_timestamps else "")
            + (f"[ {level} ] " if level != "INFO" else "")
            + f"{msg}\n"
        )

    def message(self, message: LogMessage) -> None:
        level = message["level"]
        current_frame = self.full_stack_frames[0] if self.full_stack_frames else None

        if self.output_messages or (
            current_frame is not None and current_frame.type != "KEYWORD" and level in ["FAIL", "ERROR", "WARN"]
        ):
            self._send_log_event(message["timestamp"], level, message["message"], "messages")

    def get_scopes(self, frame_id: int) -> List[Scope]:
        result: List[Scope] = []
        entry = next((v for v in self.stack_frames if v.id == frame_id), None)
        if entry is not None:
            context = entry.context()
            if context is not None:
                result.append(
                    Scope(
                        name="Local",
                        expensive=False,
                        presentation_hint="local",
                        variables_reference=entry.local_id,
                    )
                )
                if context.variables._test is not None and entry.type == "KEYWORD":
                    result.append(
                        Scope(
                            name="Test",
                            expensive=False,
                            presentation_hint="test",
                            variables_reference=entry.test_id,
                        )
                    )
                if context.variables._suite is not None and entry.type in [
                    "TEST",
                    "KEYWORD",
                ]:
                    result.append(
                        Scope(
                            name="Suite",
                            expensive=False,
                            presentation_hint="suite",
                            variables_reference=entry.suite_id,
                        )
                    )
                if context.variables._global is not None:
                    result.append(
                        Scope(
                            name="Global",
                            expensive=False,
                            presentation_hint="global",
                            variables_reference=entry.global_id,
                        )
                    )

        return result

    _cache_id_manager = IdManager()

    def _new_cache_id(self) -> int:
        o = MarkerObject()
        self._variables_object_cache.append(o)
        return StackFrameEntry._id_manager.get_id(o)

    debug_repr = DebugRepr()

    def _create_variable(
        self, name: str, value: Any, presentation_hint: Optional[VariablePresentationHint] = None
    ) -> Variable:
        if isinstance(value, Mapping):
            v_id = self._new_cache_id()
            self._variables_cache[v_id] = value
            return Variable(
                name=name,
                value=self.debug_repr.repr(value),
                type=repr(type(value)),
                variables_reference=v_id,
                named_variables=len(value) + 1,
                indexed_variables=0,
                presentation_hint=(
                    presentation_hint if presentation_hint is not None else VariablePresentationHint(kind="data")
                ),
            )

        if isinstance(value, Sequence) and not isinstance(value, str):
            v_id = self._new_cache_id()
            self._variables_cache[v_id] = value
            return Variable(
                name=name,
                value=self.debug_repr.repr(value),
                type=repr(type(value)),
                variables_reference=v_id,
                named_variables=1,
                indexed_variables=len(value),
                presentation_hint=VariablePresentationHint(kind="data"),
            )

        return Variable(name=name, value=self.debug_repr.repr(value), type=repr(type(value)))

    if get_robot_version() >= (7, 0):

        def get_handler_args(self, handler: UserKeywordHandler) -> Any:
            return handler.args

    else:

        def get_handler_args(self, handler: UserKeywordHandler) -> Any:
            return handler.arguments

    def get_variables(
        self,
        variables_reference: int,
        filter: Optional[Literal["indexed", "named"]] = None,
        start: Optional[int] = None,
        count: Optional[int] = None,
        format: Optional[ValueFormat] = None,
    ) -> List[Variable]:
        if filter is None:
            return self._get_variables_no_filter(variables_reference)
        if filter == "indexed":
            return self._get_variables_indexed(variables_reference, start, count)
        if filter == "named":
            return self._get_variables_named(variables_reference, start, count)

        raise ValueError(f"Unknown filter: {filter}")

    def _get_variables_no_filter(self, variables_reference: int) -> List[Variable]:
        result: MutableMapping[str, Any] = {}
        entry = next(
            (v for v in self.stack_frames if variables_reference in [v.global_id, v.suite_id, v.test_id, v.local_id]),
            None,
        )
        if entry is not None:
            context = entry.context()
            if context is not None:
                if entry.global_id == variables_reference:
                    result.update(
                        {k: self._create_variable(k, v) for k, v in context.variables._global.as_dict().items()}
                    )
                elif entry.suite_id == variables_reference:
                    result.update(self._get_suite_variables(context, entry))
                elif entry.test_id == variables_reference:
                    result.update(self._get_test_variables(context, entry))
                elif entry.local_id == variables_reference:
                    result.update(self._get_local_variables(context, entry))
        else:
            value = self._variables_cache.get(variables_reference, None)
            result.update(self._get_cached_variables(value))
        return list(result.values())

    def _get_suite_variables(self, context: Any, entry: Any) -> MutableMapping[str, Variable]:
        result: MutableMapping[str, Variable] = {}
        globals = context.variables._global.as_dict()
        vars = entry.get_first_or_self().variables()
        vars_dict = vars.as_dict() if vars is not None else {}
        for k, v in context.variables._suite.as_dict().items():
            if (k not in globals or globals[k] != v) and (k in vars_dict):
                result[k] = self._create_variable(k, v)
        return result

    def _get_test_variables(self, context: Any, entry: Any) -> MutableMapping[str, Variable]:
        result: MutableMapping[str, Variable] = {}
        globals = context.variables._suite.as_dict()
        vars = entry.get_first_or_self().variables()
        vars_dict = vars.as_dict() if vars is not None else {}
        for k, v in context.variables._test.as_dict().items():
            if (k not in globals or globals[k] != v) and (k in vars_dict):
                result[k] = self._create_variable(k, v)
        return result

    def _get_local_variables(self, context: Any, entry: Any) -> MutableMapping[str, Variable]:
        result: MutableMapping[str, Variable] = {}
        vars = entry.get_first_or_self().variables()
        if self._current_exception is not None:
            result["${EXCEPTION}"] = self._create_variable(
                "${EXCEPTION}",
                self._current_exception,
                VariablePresentationHint(kind="virtual"),
            )
        if vars is not None:
            p = entry.parent() if entry.parent else None
            globals = (
                (p.get_first_or_self().variables() if p is not None else None)
                or context.variables._test
                or context.variables._suite
                or context.variables._global
            ).as_dict()
            suite_vars = (context.variables._suite or context.variables._global).as_dict()
            for k, v in vars.as_dict().items():
                if (k not in globals or globals[k] != v) and (
                    entry.handler is None or k not in suite_vars or suite_vars[k] != v
                ):
                    result[k] = self._create_variable(k, v)
            if entry.handler is not None and self.get_handler_args(entry.handler):
                for argument in self.get_handler_args(entry.handler).argument_names:
                    name = f"${{{argument}}}"
                    try:
                        value = vars[name]
                    except (SystemExit, KeyboardInterrupt):
                        raise
                    except BaseException as e:
                        value = str(e)
                    result[name] = self._create_variable(name, value)
        return result

    def _get_cached_variables(self, value: Any) -> MutableMapping[str, Variable]:
        result: MutableMapping[str, Variable] = {}
        if value is not None and isinstance(value, Mapping):
            result["len()"] = self._create_variable("len()", len(value))
            for i, (k, v) in enumerate(value.items()):
                result[repr(i)] = self._create_variable(repr(k), v)
                if i >= MAX_VARIABLE_ITEMS_DISPLAY:
                    result["Unable to handle"] = self._create_variable(
                        "Unable to handle",
                        f"Maximum number of items ({MAX_VARIABLE_ITEMS_DISPLAY}) reached.",
                    )
                    break
        elif value is not None and isinstance(value, Sequence) and not isinstance(value, str):
            result["len()"] = self._create_variable("len()", len(value))
        return result

    def _get_variables_indexed(
        self,
        variables_reference: int,
        start: Optional[int],
        count: Optional[int],
    ) -> List[Variable]:
        result: MutableMapping[str, Any] = {}
        value = self._variables_cache.get(variables_reference, None)
        if value is not None:
            c = 0
            padding = len(str(len(value)))
            for i, v in enumerate(value[start:], start or 0):
                result[str(i)] = self._create_variable(str(i).zfill(padding), v)
                c += 1
                if count is not None and c >= count:
                    break
        return list(result.values())

    def _get_variables_named(
        self,
        variables_reference: int,
        start: Optional[int],
        count: Optional[int],
    ) -> List[Variable]:
        result: MutableMapping[str, Any] = {}
        value = self._variables_cache.get(variables_reference, None)
        if value is not None and isinstance(value, Mapping):
            for i, (k, v) in enumerate(value.items(), start or 0):
                result[repr(i)] = self._create_variable(repr(k), v)
                if count is not None and i >= count:
                    break
        elif value is not None and isinstance(value, Sequence) and not isinstance(value, str):
            result["len()"] = self._create_variable("len()", len(value))
        return list(result.values())

    IS_VARIABLE_RE: ClassVar = re.compile(r"^[$@&]\{.*\}(\[[^\]]*\])?$")
    IS_VARIABLE_ASSIGNMENT_RE: ClassVar = re.compile(r"^[$@&]\{.*\}=?$")
    SPLIT_LINE: ClassVar = re.compile(r"(?= {2,}| ?\t)\s*")
    CURRDIR: ClassVar = re.compile(r"(?i)\$\{CURDIR\}")

    if get_robot_version() >= (7, 0):

        def _run_keyword(self, kw: Keyword, context: Any) -> Any:
            return kw.run(context.steps[-1][1], context)

    else:

        def _run_keyword(self, kw: Keyword, context: Any) -> Any:
            return kw.run(context)

    if get_robot_version() >= (7, 2):

        @staticmethod
        def check_message_is_logged(listener: Any, msg: Any) -> bool:
            return cast(bool, listener._is_logged(msg))

    else:

        @staticmethod
        def check_message_is_logged(listener: Any, msg: Any) -> bool:
            return cast(bool, listener._is_logged(msg.level))

    def evaluate(
        self,
        expression: str,
        frame_id: Optional[int] = None,
        context: Union[EvaluateArgumentContext, str, None] = None,
        format: Optional[ValueFormat] = None,
    ) -> EvaluateResult:
        """Evaluate an expression in the context of a stack frame."""
        if not expression:
            return EvaluateResult(result="")

        # Handle expression mode toggle
        if self._is_expression_mode_toggle(expression, context):
            self.expression_mode = not self.expression_mode
            return EvaluateResult(result="# Expression mode is now " + ("on" if self.expression_mode else "off"))

        # Get evaluation context
        stack_frame, evaluate_context = self._get_evaluation_context(frame_id)
        if evaluate_context is None:
            return EvaluateResult(result="Unable to evaluate expression. No context available.", type="FatalError")

        # Process CURDIR substitution
        processed_expression = self._process_curdir_substitution(expression, stack_frame)
        if isinstance(processed_expression, EvaluateResult):
            return processed_expression

        # Get variables context
        vars = self._get_variables_context(stack_frame, evaluate_context)

        # Evaluate expression
        try:
            if self._is_expression_mode(context):
                result = self._evaluate_expression_mode(processed_expression, vars, evaluate_context, context)
            else:
                result = self._evaluate_repl_mode(processed_expression, vars, evaluate_context)

        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._logger.exception(e)
            raise

        return self._create_evaluate_result(result)

    def _is_expression_mode_toggle(self, expression: str, context: Union[EvaluateArgumentContext, str, None]) -> bool:
        """Check if expression is a command to toggle expression mode."""
        return (
            (context == EvaluateArgumentContext.REPL)
            and expression.startswith("#")
            and expression[1:].strip() == "exprmode"
        )

    def _get_evaluation_context(self, frame_id: Optional[int]) -> tuple[Optional[StackFrameEntry], Any]:
        """Get the stack frame and evaluation context for the given frame ID."""
        stack_frame = next((v for v in self.full_stack_frames if v.id == frame_id), None)
        evaluate_context = stack_frame.context() if stack_frame else None

        if evaluate_context is None:
            evaluate_context = EXECUTION_CONTEXTS.current

        return stack_frame, evaluate_context

    def _process_curdir_substitution(
        self, expression: str, stack_frame: Optional[StackFrameEntry]
    ) -> Union[str, EvaluateResult]:
        """Process ${CURDIR} substitution in expression."""
        if stack_frame is not None and stack_frame.source is not None:
            curdir = str(Path(stack_frame.source).parent)
            expression = self.CURRDIR.sub(curdir.replace("\\", "\\\\"), expression)
            if expression == curdir:
                return EvaluateResult(repr(expression), repr(type(expression)))
        return expression

    def _get_variables_context(self, stack_frame: Optional[StackFrameEntry], evaluate_context: Any) -> Any:
        """Get the variables context for evaluation."""
        return (
            (stack_frame.get_first_or_self().variables() or evaluate_context.variables.current)
            if stack_frame is not None
            else evaluate_context.variables._global
        )

    def _is_expression_mode(self, context: Union[EvaluateArgumentContext, str, None]) -> bool:
        """Check if we should use expression mode for evaluation."""
        return (
            isinstance(context, EvaluateArgumentContext) and context != EvaluateArgumentContext.REPL
        ) or self.expression_mode

    def _evaluate_expression_mode(
        self, expression: str, vars: Any, evaluate_context: Any, context: Union[EvaluateArgumentContext, str, None]
    ) -> Any:
        """Evaluate expression in expression mode."""
        if expression.startswith("! "):
            return self._evaluate_keyword_expression(expression, evaluate_context)
        if self.IS_VARIABLE_RE.match(expression.strip()):
            return self._evaluate_variable_expression(expression, vars, context)
        return internal_evaluate_expression(vars.replace_string(expression), vars)

    def _evaluate_keyword_expression(self, expression: str, evaluate_context: Any) -> Any:
        """Evaluate a keyword expression (starting with '! ')."""
        splitted = self.SPLIT_LINE.split(expression[2:].strip())

        if not splitted:
            return None

        # Extract variable assignments
        variables: List[str] = []
        while len(splitted) > 1 and self.IS_VARIABLE_ASSIGNMENT_RE.match(splitted[0].strip()):
            var = splitted[0]
            splitted = splitted[1:]
            if var.endswith("="):
                var = var[:-1]
            variables.append(var)

        if not splitted:
            return None

        def run_kw() -> Any:
            kw = Keyword(
                name=splitted[0],
                args=tuple(splitted[1:]),
                assign=tuple(variables),
            )
            return self._run_keyword(kw, evaluate_context)

        result = self.run_in_robot_thread(run_kw)

        if isinstance(result, BaseException):
            raise result

        return result

    def _evaluate_variable_expression(
        self, expression: str, vars: Any, context: Union[EvaluateArgumentContext, str, None]
    ) -> Any:
        """Evaluate a variable expression."""
        try:
            return vars.replace_scalar(expression)
        except VariableError:
            if self._should_return_undefined_for_variable_error(context):
                return UNDEFINED
            raise

    def _should_return_undefined_for_variable_error(self, context: Union[EvaluateArgumentContext, str, None]) -> bool:
        """Check if we should return UNDEFINED for variable errors in certain contexts."""
        return context is not None and (
            (
                isinstance(context, EvaluateArgumentContext)
                and context in [EvaluateArgumentContext.HOVER, EvaluateArgumentContext.WATCH]
            )
            or context in [EvaluateArgumentContext.HOVER.value, EvaluateArgumentContext.WATCH.value]
        )

    def _evaluate_repl_mode(self, expression: str, vars: Any, evaluate_context: Any) -> Any:
        """Evaluate expression in REPL mode."""
        parts = self.SPLIT_LINE.split(expression.strip())
        if parts and len(parts) == 1 and self.IS_VARIABLE_RE.match(parts[0].strip()):
            return vars.replace_scalar(parts[0].strip())
        return self._evaluate_test_body_expression(expression, evaluate_context)

    def _evaluate_test_body_expression(self, expression: str, evaluate_context: Any) -> Any:
        """Evaluate a test body expression (Robot Framework commands)."""

        def get_test_body_from_string(command: str) -> TestCase:
            suite_str = (
                "*** Test Cases ***\nDummyTestCase423141592653589793\n  "
                + ("\n  ".join(command.split("\n")) if "\n" in command else command)
            ) + "\n"

            model = get_model(suite_str)
            suite: TestSuite = TestSuite.from_model(model)
            return cast(TestCase, suite.tests[0])

        def run_kw() -> Any:
            test = get_test_body_from_string(expression)
            result = None

            if len(test.body):
                if get_robot_version() >= (7, 3):
                    result = self._execute_keywords_with_delayed_logging_v73(test.body, evaluate_context)
                else:
                    result = self._execute_keywords_with_delayed_logging_legacy(test.body, evaluate_context)
            return result

        result = self.run_in_robot_thread(run_kw)

        if isinstance(result, BaseException):
            raise result

        return result

    def _execute_keywords_with_delayed_logging_v73(self, keywords: Any, evaluate_context: Any) -> Any:
        """Execute keywords with delayed logging for Robot Framework >= 7.3."""
        result = None
        for kw in keywords:
            with evaluate_context.output.delayed_logging:
                try:
                    result = self._run_keyword(kw, evaluate_context)
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as e:
                    result = e
                    break
        return result

    def _execute_keywords_with_delayed_logging_legacy(self, keywords: Any, evaluate_context: Any) -> Any:
        """Execute keywords with delayed logging for Robot Framework < 7.3."""
        result = None
        for kw in keywords:
            with LOGGER.delayed_logging:
                try:
                    result = self._run_keyword(kw, evaluate_context)
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as e:
                    result = e
                    break
                finally:
                    if get_robot_version() <= (7, 2):
                        self._process_delayed_log_messages()
        return result

    def _process_delayed_log_messages(self) -> None:
        """Process delayed log messages for older Robot Framework versions."""
        messages = LOGGER._log_message_cache or []
        for msg in messages or ():
            listener: Any = next(iter(LOGGER), None)
            if listener is None or self.check_message_is_logged(listener, msg):
                self.log_message(
                    {
                        "level": msg.level,
                        "message": msg.message,
                        "timestamp": msg.timestamp,
                    }
                )

    def _create_evaluate_result(self, value: Any) -> EvaluateResult:
        if isinstance(value, Mapping):
            v_id = self._new_cache_id()
            self._variables_cache[v_id] = value
            return EvaluateResult(
                result=reprlib.repr(value),
                type=repr(type(value)),
                variables_reference=v_id,
                named_variables=len(value) + 1,
                indexed_variables=0,
            )

        if isinstance(value, Sequence) and not isinstance(value, str):
            v_id = self._new_cache_id()
            self._variables_cache[v_id] = value
            return EvaluateResult(
                result=reprlib.repr(value),
                type=repr(type(value)),
                variables_reference=v_id,
                named_variables=1,
                indexed_variables=len(value),
            )

        return EvaluateResult(result=repr(value), type=repr(type(value)))

    def run_in_robot_thread(self, kw: KeywordCallable) -> EvaluationResult:
        with self.condition:
            self._keyword_to_evaluate = kw
            self._evaluated_keyword_result = None

            self._evaluate_keyword_event.clear()
            self._after_evaluate_keyword_event.clear()

            old_state = self.state
            self.state = State.CallKeyword
            self.condition.notify_all()

        try:
            self._evaluate_keyword_event.wait(KEYWORD_EVALUATION_TIMEOUT)
        finally:
            result = self._evaluated_keyword_result

            with self.condition:
                self._keyword_to_evaluate = None
                self._evaluated_keyword_result = None

                self.state = old_state
                self.condition.notify_all()

                self._after_evaluate_keyword_event.set()

            return result

    def _create_set_variable_result(self, value: Any) -> SetVariableResult:
        if isinstance(value, Mapping):
            v_id = self._new_cache_id()
            self._variables_cache[v_id] = value
            return SetVariableResult(
                value=reprlib.repr(value),
                type=repr(type(value)),
                variables_reference=v_id,
                named_variables=len(value) + 1,
                indexed_variables=0,
            )

        if isinstance(value, Sequence) and not isinstance(value, str):
            v_id = self._new_cache_id()
            self._variables_cache[v_id] = value
            return SetVariableResult(
                value=reprlib.repr(value),
                type=repr(type(value)),
                variables_reference=v_id,
                named_variables=1,
                indexed_variables=len(value),
            )

        return SetVariableResult(value=repr(value), type=repr(type(value)))

    def set_variable(
        self,
        variables_reference: int,
        name: str,
        value: str,
        format: Optional[ValueFormat] = None,
    ) -> SetVariableResult:
        entry = next(
            (
                v
                for v in self.full_stack_frames
                if variables_reference in [v.global_id, v.local_id, v.suite_id, v.test_id]
            ),
            None,
        )

        if entry is not None:
            context = entry.context()
            if context is not None:
                variables = context.variables.current

                if (name[2:-1] if self.IS_VARIABLE_RE.match(name) else name) not in variables:
                    raise NameError(f"Variable '{name}' not found.")

                evaluated_value = internal_evaluate_expression(variables.replace_string(value), variables)
                variables[name] = evaluated_value

                return self._create_set_variable_result(evaluated_value)

        raise ReferenceError("Invalid variable reference.")

    def set_exception_breakpoints(
        self,
        filters: List[str],
        filter_options: Optional[List[ExceptionFilterOptions]] = None,
        exception_options: Optional[List[ExceptionOptions]] = None,
    ) -> Optional[List[Breakpoint]]:
        self.exception_breakpoints.clear()

        result: List[Breakpoint] = []

        if filter_options is not None:
            for option in filter_options:
                if option.filter_id in [
                    "failed_keyword",
                    "uncaught_failed_keyword",
                    "",
                    "failed_suite",
                ]:
                    entry = ExceptionBreakpointsEntry(
                        tuple(filters),
                        tuple(filter_options) if filter_options is not None else None,
                        tuple(exception_options) if exception_options is not None else None,
                    )

                    self.exception_breakpoints.add(entry)
                    result.append(Breakpoint(verified=True))
                else:
                    result.append(Breakpoint(verified=False))

        return result or None

    if get_robot_version() >= (7, 0):

        def _get_keywords_from_lib(self, lib: Any) -> Any:
            return lib.keywords

        def _get_short_doc_from_kw(self, kw: Any) -> Any:
            return kw.short_doc

    else:

        def _get_keywords_from_lib(self, lib: Any) -> Any:
            return lib.handlers

        def _get_short_doc_from_kw(self, kw: Any) -> Any:
            return kw.shortdoc

    def completions(
        self,
        text: str,
        column: int,
        line: Optional[int] = None,
        frame_id: Optional[int] = None,
    ) -> List[CompletionItem]:
        if self.expression_mode:
            return []

        stack_frame = next((v for v in self.full_stack_frames if v.id == frame_id), None)

        evaluate_context = stack_frame.context() if stack_frame else None

        if evaluate_context is None:
            evaluate_context = EXECUTION_CONTEXTS.current

        if evaluate_context is None:
            return []

        result = []

        for library in evaluate_context.namespace._kw_store.libraries.values():
            result.append(
                CompletionItem(
                    label=library.name,
                    text=library.name,
                    sort_text=f"020_{library.name}",
                    type=CompletionItemType.MODULE,
                )
            )
            for kw in self._get_keywords_from_lib(library):
                result.append(
                    CompletionItem(
                        label=kw.name,
                        text=kw.name,
                        sort_text=f"001_{kw.name}",
                        type=CompletionItemType.FUNCTION,
                        detail=self._get_short_doc_from_kw(kw),
                    )
                )

        for resource in evaluate_context.namespace._kw_store.resources.values():
            result.append(
                CompletionItem(
                    label=resource.name,
                    text=resource.name,
                    sort_text=f"020_{resource.name}",
                    type=CompletionItemType.MODULE,
                )
            )
            for kw in self._get_keywords_from_lib(resource):
                result.append(
                    CompletionItem(
                        label=kw.name,
                        text=kw.name,
                        sort_text=f"001_{kw.name}",
                        type=CompletionItemType.FUNCTION,
                        detail=self._get_short_doc_from_kw(kw),
                    )
                )

        for var in evaluate_context.variables.as_dict().keys():
            result.append(
                CompletionItem(
                    label=var,
                    text=var,
                    sort_text=f"010_{var}",
                    type=CompletionItemType.VARIABLE,
                )
            )
        return result
