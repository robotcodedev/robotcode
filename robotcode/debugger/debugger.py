from __future__ import annotations

import itertools
import os
import pathlib
import re
import threading
import weakref
from collections import deque
from enum import Enum
from pathlib import Path, PurePath
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Generator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

from ..utils.event import event
from ..utils.logging import LoggingDescriptor
from .dap_types import (
    Breakpoint,
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


class Undefined:
    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "<undefined>"


UNDEFINED = Undefined()


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


class InvalidThreadId(Exception):
    def __init__(self, thread_id: Any) -> None:
        super().__init__(f"Invalid thread id {thread_id}")


class StackFrameEntry:
    def __init__(
        self,
        parent: Optional[StackFrameEntry],
        context: Any,
        name: str,
        type: str,
        source: Optional[str],
        line: Optional[int],
        column: Optional[int] = None,
        handler: Any = None,
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
        self._suite_marker = object()
        self._test_marker = object()
        self._local_marker = object()
        self._global_marker = object()
        self.stack_frames: Deque[StackFrameEntry] = deque()

    def __repr__(self) -> str:
        return (
            f"StackFrameEntry({repr(self.name)}, {repr(self.type)}, "
            + f"{repr(self.source)}, {repr(self.line)}, {repr(self.column)})"
        )

    def get_first_or_self(self) -> StackFrameEntry:
        if self.stack_frames:
            return self.stack_frames[0]
        return self

    @property
    def id(self) -> int:
        return id(self)

    def test_id(self) -> int:
        return id(self._test_marker)

    def suite_id(self) -> int:
        return id(self._suite_marker)

    def local_id(self) -> int:
        return id(self._local_marker)

    def global_id(self) -> int:
        return id(self._global_marker)


class HitCountEntry(NamedTuple):
    source: pathlib.PurePath
    line: int
    type: str


class PathMapping(NamedTuple):
    local_root: Optional[str]
    remote_root: Optional[str]


class Debugger:
    __instance = None
    __lock = threading.RLock()
    __inside_instance = False

    _logger = LoggingDescriptor()

    @classmethod
    def instance(cls) -> Debugger:
        if cls.__instance is not None:
            return cls.__instance
        with cls.__lock:
            # re-check, perhaps it was created in the mean time...
            if cls.__instance is None:
                cls.__inside_instance = True
                try:
                    cls.__instance = cls()
                finally:
                    cls.__inside_instance = False
        return cls.__instance

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
        self.state: State = State.Stopped
        self.requested_state: RequestedState = RequestedState.Nothing
        self.stop_stack_len = 0
        self._robot_report_file: Optional[str] = None
        self._robot_log_file: Optional[str] = None
        self._robot_output_file: Optional[str] = None
        self.output_messages: bool = False
        self.output_log: bool = False
        self.group_output: bool = False
        self.hit_counts: Dict[HitCountEntry, int] = {}
        self.last_fail_message: Optional[str] = None
        self.stop_on_entry = False
        self.no_debug = False
        self.terminated = False
        self.terminated_requested = False
        self.attached = False
        self.path_mappings: List[PathMapping] = []

        self._keyword_to_evaluate: Optional[Callable[..., Any]] = None
        self._evaluated_keyword_result: Any = None
        self._evaluate_keyword_event = threading.Event()
        self._evaluate_keyword_event.set()
        self._after_evaluate_keyword_event = threading.Event()
        self._after_evaluate_keyword_event.set()

    @property
    def debug(self) -> bool:
        return not self.no_debug

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

    @_logger.call
    def terminate_requested(self) -> None:
        self.terminated_requested = True

    @_logger.call
    def terminate(self) -> None:
        self.terminated = True

    @_logger.call
    def start(self) -> None:
        with self.condition:
            self.state = State.Running
            self.condition.notify_all()

    @_logger.call
    def stop(self) -> None:
        with self.condition:
            self.state = State.Stopped

            if self.main_thread is not None and self.main_thread.ident:
                self.send_event(
                    self,
                    ContinuedEvent(
                        body=ContinuedEventBody(thread_id=self.main_thread.ident, all_threads_continued=True)
                    ),
                )

            self.condition.notify_all()

    @_logger.call
    def continue_all(self, send_event: bool = True) -> None:
        if self.main_thread is not None and self.main_thread.ident is not None:
            self.continue_thread(self.main_thread.ident, send_event)

    @_logger.call
    def continue_thread(self, thread_id: int, send_event: bool = False) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise InvalidThreadId(thread_id)

        with self.condition:
            if send_event:
                self.send_event(
                    self,
                    ContinuedEvent(
                        body=ContinuedEventBody(thread_id=self.main_thread.ident, all_threads_continued=True)
                    ),
                )
            self.state = State.Running
            self.condition.notify_all()

    @_logger.call
    def pause_thread(self, thread_id: int) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise InvalidThreadId(thread_id)

        with self.condition:
            self.requested_state = RequestedState.Pause
            self.state = State.Paused

            self.condition.notify_all()

    @_logger.call
    def next(self, thread_id: int, granularity: Optional[SteppingGranularity] = None) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise InvalidThreadId(thread_id)

        with self.condition:
            self.state = State.Running

            if self.full_stack_frames and self.full_stack_frames[0].type in ["TEST", "SUITE"]:
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

    @_logger.call
    def step_in(
        self, thread_id: int, target_id: Optional[int] = None, granularity: Optional[SteppingGranularity] = None
    ) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise InvalidThreadId(thread_id)

        with self.condition:
            self.requested_state = RequestedState.StepIn
            self.state = State.Running

            self.condition.notify_all()

    @_logger.call
    def step_out(self, thread_id: int, granularity: Optional[SteppingGranularity] = None) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise InvalidThreadId(thread_id)

        with self.condition:
            self.requested_state = RequestedState.StepOut
            self.state = State.Running
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
    def send_event(sender, event: Event) -> None:  # NOSONAR
        ...

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
                tuple(breakpoints) if breakpoints else (), tuple(lines) if lines else ()
            )
            return [
                Breakpoint(id=id(v), source=Source(path=str(path)), verified=True, line=v.line)
                for v in result.breakpoints
            ]
        else:
            self._logger.error("not supported breakpoint")

        return []

    def process_start_state(self, source: str, line_no: int, type: str, status: str) -> None:
        from robot.running.context import EXECUTION_CONTEXTS
        from robot.variables.evaluation import evaluate_expression

        if self.state == State.Stopped:
            return

        elif self.requested_state == RequestedState.Pause:
            self.state = State.Paused
            self.send_event(
                self,
                StoppedEvent(
                    body=StoppedEventBody(
                        reason=StoppedReason.PAUSE,
                        thread_id=threading.current_thread().ident,
                    )
                ),
            )
            self.requested_state = RequestedState.Nothing
        elif self.requested_state == RequestedState.Next:
            if len(self.full_stack_frames) <= self.stop_stack_len:
                self.state = State.Paused
                self.send_event(
                    self,
                    StoppedEvent(
                        body=StoppedEventBody(
                            reason=StoppedReason.STEP,
                            thread_id=threading.current_thread().ident,
                        )
                    ),
                )
                self.requested_state = RequestedState.Nothing
        elif self.requested_state == RequestedState.StepIn:
            self.state = State.Paused
            self.send_event(
                self,
                StoppedEvent(
                    body=StoppedEventBody(
                        reason=StoppedReason.STEP,
                        thread_id=threading.current_thread().ident,
                    )
                ),
            )
            self.requested_state = RequestedState.Nothing
        elif self.requested_state == RequestedState.StepOut:
            if len(self.full_stack_frames) <= self.stop_stack_len:
                self.state = State.Paused
                self.send_event(
                    self,
                    StoppedEvent(
                        body=StoppedEventBody(
                            reason=StoppedReason.STEP,
                            thread_id=threading.current_thread().ident,
                        )
                    ),
                )
                self.requested_state = RequestedState.Nothing

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
                                hit = bool(evaluate_expression(vars.replace_string(point.condition), vars.store))
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
                        else:
                            self.state = State.Paused
                            self.send_event(
                                self,
                                StoppedEvent(
                                    body=StoppedEventBody(
                                        reason=StoppedReason.BREAKPOINT,
                                        thread_id=threading.current_thread().ident,
                                        hit_breakpoint_ids=[id(v) for v in breakpoints],
                                    )
                                ),
                            )

    def process_end_state(self, status: str, filter_id: Set[str], description: str, text: Optional[str]) -> None:
        if (
            not self.terminated
            and status == "FAIL"
            and any(
                v
                for v in self.exception_breakpoints
                if v.filter_options and any(o for o in v.filter_options if o.filter_id in filter_id)
            )
        ):
            self.state = State.Paused

            self.send_event(
                self,
                StoppedEvent(
                    body=StoppedEventBody(
                        description=description,
                        reason=StoppedReason.EXCEPTION,
                        thread_id=threading.current_thread().ident,
                        all_threads_stopped=True,
                        text=text,
                    )
                ),
            )
            self.wait_for_running()

    @_logger.call
    def wait_for_running(self) -> None:
        if self.attached:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda: self.state in [State.Running, State.Stopped, State.CallKeyword])

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
                        self._after_evaluate_keyword_event.wait(60)

                    continue
                break

    def start_output_group(self, name: str, attributes: Dict[str, Any], type: Optional[str] = None) -> None:
        if self.group_output:
            source = attributes.get("source", None)
            line_no = attributes.get("lineno", None)

            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output=f"\u001b[38;5;14m{(type +' ') if type else ''}\u001b[0m{name}\n",
                        category=OutputCategory.CONSOLE,
                        group=OutputGroup.START,
                        source=Source(path=str(self.map_path_to_client(source))) if source else None,
                        line=line_no if source is not None else None,
                        column=0 if source is not None else None,
                    )
                ),
            )

    def end_output_group(self, name: str, attributes: Dict[str, Any]) -> None:
        if self.group_output:
            source = attributes.get("source", None)
            line_no = attributes.get("lineno", None)

            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output="",
                        category=OutputCategory.CONSOLE,
                        group=OutputGroup.END,
                        source=Source(path=str(self.map_path_to_client(source))) if source else None,
                        line=line_no,
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
        handler: Any = None,
        libname: Optional[str] = None,
        kwname: Optional[str] = None,
        longname: Optional[str] = None,
    ) -> StackFrameEntry:
        from robot.running.context import EXECUTION_CONTEXTS
        from robot.running.userkeyword import UserKeywordHandler

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

        if type in ["KEYWORD"] and source is None and line is None and column is None:
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
        handler: Any = None,
    ) -> None:
        from robot.running.userkeyword import UserKeywordHandler

        self.full_stack_frames.popleft()

        if type in ["KEYWORD"] and source is None and line is None and column is None:
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

    def start_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        source = attributes.get("source", None)
        line_no = attributes.get("lineno", 1)
        longname = attributes.get("longname", "")
        status = attributes.get("status", "")
        type = "SUITE"

        entry = self.add_stackframe_entry(name, type, source, line_no, longname=longname)

        if self.debug:
            if self.stop_on_entry:
                self.stop_on_entry = False

                self.state = State.Paused
                self.send_event(
                    self,
                    StoppedEvent(
                        body=StoppedEventBody(
                            reason=StoppedReason.ENTRY,
                            thread_id=threading.current_thread().ident,
                        )
                    ),
                )

                self.wait_for_running()
            elif entry.source:
                self.process_start_state(entry.source, entry.line if entry.line is not None else 0, entry.type, status)

                self.wait_for_running()

    def end_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        if self.debug:
            status = attributes.get("status", "")

            if status == "FAIL":
                self.process_end_state(
                    status,
                    {"failed_suite"},
                    "Suite failed.",
                    f"Suite failed{f': {v}' if (v:=attributes.get('message', None)) else ''}",
                )

        source = attributes.get("source", None)
        line_no = attributes.get("lineno", 1)
        type = "SUITE"

        self.remove_stackframe_entry(name, type, source, line_no)

    def start_test(self, name: str, attributes: Dict[str, Any]) -> None:
        source = attributes.get("source", None)
        line_no = attributes.get("lineno", 1)
        longname = attributes.get("longname", "")
        status = attributes.get("status", "")

        type = "TEST"

        entry = self.add_stackframe_entry(name, type, source, line_no, longname=longname)

        if self.debug and entry.source:
            self.process_start_state(entry.source, entry.line if entry.line is not None else 0, entry.type, status)

            self.wait_for_running()

    def end_test(self, name: str, attributes: Dict[str, Any]) -> None:
        if self.debug:
            status = attributes.get("status", "")

            if status == "FAIL":
                self.process_end_state(
                    status,
                    {"failed_test"},
                    "Test failed.",
                    f"Test failed{f': {v}' if (v:=attributes.get('message', None)) else ''}",
                )

        source = attributes.get("source", None)
        line_no = attributes.get("lineno", 1)
        longname = attributes.get("longname", "")
        type = "TEST"

        self.remove_stackframe_entry(longname, type, source, line_no)

    def start_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        from robot.running.context import EXECUTION_CONTEXTS

        status = attributes.get("status", "")
        source = attributes.get("source", None)
        line_no = attributes.get("lineno", None)
        type = attributes.get("type", "KEYWORD")
        libname = attributes.get("libname", None)
        kwname = attributes.get("kwname", None)

        handler: Any = None
        if type in ["KEYWORD", "SETUP", "TEARDOWN"]:
            try:
                handler = EXECUTION_CONTEXTS.current.namespace.get_runner(name)._handler
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass

        entry = self.add_stackframe_entry(
            kwname, type, source, line_no, handler=handler, libname=libname, kwname=kwname, longname=name
        )

        if status == "NOT RUN" and type not in ["IF"]:
            return

        if self.debug and entry.source and entry.line is not None:
            self.process_start_state(entry.source, entry.line, entry.type, status)

            self.wait_for_running()

    CAUGHTED_KEYWORDS = [
        "BuiltIn.Run Keyword And Expect Error",
        "BuiltIn.Run Keyword And Ignore Error",
        "BuiltIn.Run Keyword And Warn On Failure",
        "BuiltIn.Wait Until Keyword Succeeds",
        "BuiltIn.Run Keyword And Continue On Failure",
    ]

    def in_caughted_keyword(self) -> bool:
        r = next(
            (
                v
                for v in itertools.islice(self.full_stack_frames, 1, None)
                if v.type == "KEYWORD" and v.longname in self.CAUGHTED_KEYWORDS
            ),
            None,
        )
        return r is None

    def end_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        from robot.running.context import EXECUTION_CONTEXTS

        type = attributes.get("type", None)
        if self.debug:
            status = attributes.get("status", "")

            if status == "FAIL" and type in ["KEYWORD", "SETUP", "TEARDOWN"]:
                self.process_end_state(
                    status,
                    {"failed_keyword", *({"uncaught_failed_keyword"} if self.in_caughted_keyword() else {})},
                    "Keyword failed.",
                    f"Keyword failed: {self.last_fail_message}" if self.last_fail_message else "Keyword failed.",
                )

        source = attributes.get("source", None)
        line_no = attributes.get("lineno", None)
        type = attributes.get("type", "KEYWORD")
        kwname = attributes.get("kwname", None)

        handler: Any = None
        if type in ["KEYWORD", "SETUP", "TEARDOWN"]:
            try:
                handler = EXECUTION_CONTEXTS.current.namespace.get_runner(name)._handler
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass

        self.remove_stackframe_entry(kwname, type, source, line_no, handler=handler)

    def set_main_thread(self, thread: threading.Thread) -> None:
        self.main_thread = thread

    def get_threads(self) -> List[Thread]:
        main_thread = self.main_thread or threading.main_thread()

        return [Thread(id=main_thread.ident if main_thread.ident else 0, name=main_thread.name or "")]

    WINDOW_PATH_REGEX = re.compile(r"^(([a-z]:[\\/])|(\\\\)).*$", re.RegexFlag.IGNORECASE)

    @classmethod
    def is_windows_path(cls, path: Union[os.PathLike[str], str]) -> bool:
        return bool(cls.WINDOW_PATH_REGEX.fullmatch(str(path)))

    @staticmethod
    def relative_to(path: pathlib.PurePath, *other: pathlib.PurePath) -> Optional[pathlib.PurePath]:
        try:
            return path.relative_to(*other)
        except ValueError:
            return None

    def map_path_to_client(self, path: Union[os.PathLike[str], str]) -> pathlib.PurePath:
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
                else:
                    return pathlib.PurePath(mapping.local_root, relative_path)

        return path

    def get_stack_trace(
        self,
        thread_id: int,
        start_frame: Optional[int] = None,
        levels: Optional[int] = None,
        format: Optional[StackFrameFormat] = None,
    ) -> StackTraceResult:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise InvalidThreadId(thread_id)

        start_frame = start_frame or 0
        levels = start_frame + (levels or len(self.stack_frames))

        def source_from_entry(entry: StackFrameEntry) -> Optional[Source]:
            if entry.source is not None and entry.is_file:
                return Source(path=str(self.map_path_to_client(entry.source)))
            else:
                return None

        def yield_stack() -> Generator[StackFrame, None, None]:
            for i, v in enumerate(itertools.islice(self.stack_frames, start_frame, levels)):
                if v.stack_frames:
                    yield StackFrame(
                        id=v.id,
                        name=v.longname or v.kwname or v.name or v.type,
                        line=v.stack_frames[0].line if v.stack_frames[0].line is not None else 0,
                        column=v.stack_frames[0].column if v.stack_frames[0].column is not None else 1,
                        source=source_from_entry(v.stack_frames[0]),
                        presentation_hint="normal" if v.stack_frames[0].is_file else "subtle",
                        module_id=v.libname,
                    )
                if not v.top_hidden:
                    yield StackFrame(
                        id=v.id,
                        name=v.longname or v.kwname or v.name or v.type,
                        line=v.line if v.line is not None else 1,
                        column=v.column if v.column is not None else 1,
                        source=source_from_entry(v),
                        presentation_hint="normal" if v.is_file else "subtle",
                        module_id=v.libname,
                    )

        frames = list(yield_stack())

        return StackTraceResult(frames, len(self.stack_frames))

    MESSAGE_COLORS = {
        "INFO": "\u001b[38;5;2m",
        "WARN": "\u001b[38;5;3m",
        "ERROR": "\u001b[38;5;1m",
        "TRACE": "\u001b[38;5;4m",
        "FAIL": "\u001b[38;5;5m\u001b[1m",
        "DEBUG": "\u001b[38;5;8m",
    }

    def log_message(self, message: Dict[str, Any]) -> None:
        level = message["level"]
        msg = message["message"]

        if message["level"] == "FAIL":
            self.last_fail_message = msg

        current_frame = self.full_stack_frames[0] if self.full_stack_frames else None
        source = (
            Source(path=str(self.map_path_to_client(current_frame.source)))
            if current_frame and current_frame.source
            else None
        )
        line = current_frame.line if current_frame else None

        if self.output_log:
            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output=f"\u001b[38;5;237m{message['timestamp'].split(' ', 1)[1]}"
                        f" {self.MESSAGE_COLORS.get(level, '')}{level}\u001b[0m: {msg}\n",
                        category=OutputCategory.CONSOLE,
                        source=source,
                        line=line if line is not None else 0,
                        column=0 if source is not None else None,
                    )
                ),
            )

    def message(self, message: Dict[str, Any]) -> None:
        if self.output_messages:
            level = message["level"]
            msg = message["message"]

            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output=f"\u001b[38;5;237m{message['timestamp'].split(' ', 1)[1]}"
                        f" {self.MESSAGE_COLORS.get(level, '')}{level}\u001b[0m: {msg}\n",
                        category="messages",
                    )
                ),
            )

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
                        variables_reference=entry.local_id(),
                    )
                )
                if context.variables._test is not None and entry.type in ["KEYWORD"]:
                    result.append(
                        Scope(
                            name="Test",
                            expensive=False,
                            presentation_hint="test",
                            variables_reference=entry.test_id(),
                        )
                    )
                if context.variables._suite is not None and entry.type in ["TEST", "KEYWORD"]:
                    result.append(
                        Scope(
                            name="Suite",
                            expensive=False,
                            presentation_hint="suite",
                            variables_reference=entry.suite_id(),
                        )
                    )
                if context.variables._global is not None:
                    result.append(
                        Scope(
                            name="Global",
                            expensive=False,
                            presentation_hint="global",
                            variables_reference=entry.global_id(),
                        )
                    )

        return result

    def get_variables(
        self,
        variables_reference: int,
        filter: Optional[Literal["indexed", "named"]] = None,
        start: Optional[int] = None,
        count: Optional[int] = None,
        format: Optional[ValueFormat] = None,
    ) -> List[Variable]:
        from robot.utils.normalizing import NormalizedDict

        result = NormalizedDict(ignore="_")

        entry = next(
            (
                v
                for v in self.stack_frames
                if variables_reference in [v.global_id(), v.suite_id(), v.test_id(), v.local_id()]
            ),
            None,
        )
        if entry is not None:
            context = entry.context()
            if context is not None:
                if entry.global_id() == variables_reference:
                    result.update(
                        {
                            k: Variable(name=k, value=repr(v), type=repr(type(v)))
                            for k, v in context.variables._global.as_dict().items()
                        }
                    )
                elif entry.suite_id() == variables_reference:
                    globals = context.variables._global.as_dict()
                    result.update(
                        {
                            k: Variable(name=k, value=repr(v), type=repr(type(v)))
                            for k, v in context.variables._suite.as_dict().items()
                            if k not in globals or globals[k] != v
                        }
                    )
                elif entry.test_id() == variables_reference:
                    globals = context.variables._suite.as_dict()
                    result.update(
                        {
                            k: Variable(name=k, value=repr(v), type=repr(type(v)))
                            for k, v in context.variables._test.as_dict().items()
                            if k not in globals or globals[k] != v
                        }
                    )
                elif entry.local_id() == variables_reference:
                    vars = entry.get_first_or_self().variables()
                    if vars is not None:
                        p = entry.parent() if entry.parent else None

                        globals = (
                            (p.get_first_or_self().variables() if p is not None else None)
                            or context.variables._test
                            or context.variables._suite
                            or context.variables._global
                        ).as_dict()

                        suite_vars = (context.variables._suite or context.variables._global).as_dict()

                        result.update(
                            {
                                k: Variable(name=k, value=repr(v), type=repr(type(v)))
                                for k, v in vars.as_dict().items()
                                if (k not in globals or globals[k] != v)
                                and (entry.handler is None or k not in suite_vars or suite_vars[k] != v)
                            }
                        )

                        if entry.handler is not None and entry.handler.arguments:
                            for argument in entry.handler.arguments.argument_names:
                                name = f"${{{argument}}}"
                                try:
                                    value = vars[name]
                                except (SystemExit, KeyboardInterrupt):
                                    raise
                                except BaseException as e:
                                    value = str(e)

                                result[name] = Variable(name=name, value=repr(value), type=repr(type(value)))

        return list(result.values())

    IS_VARIABLE_RE = re.compile(r"^[$@&%]\{.*\}(\[[^\]]*\])?$")
    IS_VARIABLE_ASSIGNMENT_RE = re.compile(r"^[$@&%]\{.*\}=?$")
    SPLIT_LINE = re.compile(r"(?= {2,}| ?\t)\s*")
    CURRDIR = re.compile(r"(?i)\$\{CURDIR\}")

    def evaluate(
        self,
        expression: str,
        frame_id: Optional[int] = None,
        context: Union[EvaluateArgumentContext, str, None] = None,
        format: Optional[ValueFormat] = None,
    ) -> EvaluateResult:
        from robot.errors import VariableError
        from robot.running.context import EXECUTION_CONTEXTS
        from robot.running.model import Keyword
        from robot.variables.evaluation import evaluate_expression
        from robot.variables.replacer import VariableReplacer

        if not expression:
            return EvaluateResult(result="")

        stack_frame = next((v for v in self.full_stack_frames if v.id == frame_id), None)

        evaluate_context = stack_frame.context() if stack_frame else None

        if evaluate_context is None:
            evaluate_context = EXECUTION_CONTEXTS.current

        result: Any = None
        try:
            if stack_frame is not None and stack_frame.source is not None:
                curdir = str(Path(stack_frame.source).parent)
                expression = self.CURRDIR.sub(curdir.replace("\\", "\\\\"), expression)
                if expression == curdir:
                    return EvaluateResult(repr(expression), repr(type(expression)))

            vars = (
                (stack_frame.get_first_or_self().variables() or evaluate_context.variables.current)
                if stack_frame is not None
                else evaluate_context.variables._global
            )

            if expression.startswith("! "):
                splitted = self.SPLIT_LINE.split(expression[2:].strip())

                if splitted:
                    variables: List[str] = []
                    while len(splitted) > 1 and self.IS_VARIABLE_ASSIGNMENT_RE.match(splitted[0].strip()):
                        var = splitted[0]
                        splitted = splitted[1:]
                        if var.endswith("="):
                            var = var[:-1]
                        variables.append(var)

                    if splitted:

                        def run_kw() -> Any:
                            kw = Keyword(name=splitted[0], args=tuple(splitted[1:]), assign=tuple(variables))
                            return kw.run(evaluate_context)

                        with self.condition:
                            self._keyword_to_evaluate = run_kw
                            self._evaluated_keyword_result = None

                            self._evaluate_keyword_event.clear()
                            self._after_evaluate_keyword_event.clear()

                            old_state = self.state
                            self.state = State.CallKeyword
                            self.condition.notify_all()

                        try:
                            self._evaluate_keyword_event.wait(60)
                        finally:
                            result = self._evaluated_keyword_result

                            with self.condition:
                                self._keyword_to_evaluate = None
                                self._evaluated_keyword_result = None

                                self.state = old_state
                                self.condition.notify_all()

                                self._after_evaluate_keyword_event.set()

            elif self.IS_VARIABLE_RE.match(expression.strip()):
                try:
                    result = VariableReplacer(vars.store).replace_scalar(expression)
                except VariableError:
                    if context is not None and (
                        isinstance(context, EvaluateArgumentContext)
                        and (
                            context
                            in [
                                EvaluateArgumentContext.HOVER,
                                EvaluateArgumentContext.WATCH,
                            ]
                        )
                        or context
                        in [
                            EvaluateArgumentContext.HOVER.value,
                            EvaluateArgumentContext.WATCH.value,
                        ]
                    ):
                        result = UNDEFINED
                    else:
                        raise
            else:
                result = evaluate_expression(vars.replace_string(expression), vars.store)

        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            result = e

        return EvaluateResult(repr(result), repr(type(result)))

    def set_variable(
        self, variables_reference: int, name: str, value: str, format: Optional[ValueFormat] = None
    ) -> SetVariableResult:
        from robot.variables.evaluation import evaluate_expression

        entry = next(
            (
                v
                for v in self.full_stack_frames
                if variables_reference in [v.global_id(), v.local_id(), v.suite_id(), v.test_id()]
            ),
            None,
        )

        if entry is not None:
            context = entry.context()
            if context is not None:
                variables = context.variables.current

                if (name[2:-1] if self.IS_VARIABLE_RE.match(name) else name) not in variables:
                    raise NameError(f"Variable '{name}' not found.")

                evaluated_value = evaluate_expression(variables.replace_string(value), variables.store)
                variables[name] = evaluated_value

                return SetVariableResult(repr(evaluated_value), repr(type(value)))

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
                if option.filter_id in ["failed_keyword", "uncaught_failed_keyword", "failed_test", "failed_suite"]:
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
