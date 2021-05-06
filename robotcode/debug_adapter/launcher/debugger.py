from __future__ import annotations

import itertools
import re
import threading
import weakref
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Any, Deque, Dict, List, Literal, NamedTuple, Optional, Union

from ...utils.event import event
from ...utils.logging import LoggingDescriptor
from ..types import (
    Breakpoint,
    ContinuedEvent,
    ContinuedEventBody,
    EvaluateArgumentContext,
    Event,
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


class EvaluateResult(NamedTuple):
    result: str
    type: Optional[str] = None
    presentation_hint: Optional[VariablePresentationHint] = None
    variables_reference: int = 0
    named_variables: Optional[int] = None
    indexed_variables: Optional[int] = None
    memory_reference: Optional[str] = None


class State(Enum):
    Stopped = 0
    Running = 1
    Paused = 2


class RequestedState(Enum):
    Nothing = 0
    Pause = 1
    Next = 2
    StepIn = 3
    StepOut = 4


class BreakpointsEntry:
    def __init__(self, breakpoints: List[SourceBreakpoint], lines: List[int]) -> None:
        self.breakpoints = breakpoints
        self.lines = lines


class StackTraceResult(NamedTuple):
    stack_frames: List[StackFrame]
    total_frames: int


class StackFrameEntry:
    def __init__(
        self, context: weakref.ref[Any], name: str, type: str, source: Optional[str], line: int, column: int = 1
    ) -> None:
        self.context = context
        self.name = name
        self.type = type
        self.source = source
        self.line = line
        self.column = column
        self._suite_marker = object()
        self._test_marker = object()
        self._local_marker = object()
        self._global_marker = object()

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
        self.breakpoints: Dict[str, BreakpointsEntry] = {}
        self.main_thread: Optional[threading.Thread] = None
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
    def continue_thread(self, thread_id: int) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise RuntimeError("Invalid threadId")

        with self.condition:
            self.state = State.Running
            self.condition.notify_all()

    @_logger.call
    def pause_thread(self, thread_id: int) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise RuntimeError("Invalid threadId")

        with self.condition:
            self.requested_state = RequestedState.Pause
            self.state = State.Paused

            self.condition.notify_all()

    @_logger.call
    def next(self, thread_id: int, granularity: Optional[SteppingGranularity] = None) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise RuntimeError("Invalid threadId")

        with self.condition:
            self.state = State.Running

            if self.stack_frames and self.stack_frames[0].type in ["TEST", "SUITE"]:
                self.requested_state = RequestedState.StepIn
            else:
                self.requested_state = RequestedState.Next

                self.stop_stack_len = len(self.stack_frames)
                if self.stack_frames and self.stack_frames[0].type in ["FOR", "FOR ITERATION", "IF", "ELSE", "ELSE IF"]:
                    self.stop_stack_len += 1

            self.condition.notify_all()

    @_logger.call
    def step_in(
        self, thread_id: int, target_id: Optional[int] = None, granularity: Optional[SteppingGranularity] = None
    ) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise RuntimeError("Invalid threadId")

        with self.condition:
            self.requested_state = RequestedState.StepIn
            self.state = State.Running

            self.condition.notify_all()

    @_logger.call
    def step_out(self, thread_id: int, granularity: Optional[SteppingGranularity] = None) -> None:
        if self.main_thread is None or thread_id != self.main_thread.ident:
            raise RuntimeError("Invalid threadId")

        with self.condition:
            self.requested_state = RequestedState.StepOut
            self.state = State.Running
            self.stop_stack_len = len(self.stack_frames) - 1

            i = 1

            while i < len(self.stack_frames) and self.stack_frames[i].type in [
                "FOR",
                "FOR ITERATION",
                "IF",
                "ELSE",
                "ELSE IF",
            ]:
                self.stop_stack_len -= 1
                i += 1

            self.condition.notify_all()

    @event
    def send_event(sender, event: Event) -> None:
        ...

    def set_breakpoints(
        self,
        source: Source,
        breakpoints: Optional[List[SourceBreakpoint]] = None,
        lines: Optional[List[int]] = None,
        source_modified: Optional[bool] = None,
    ) -> List[Breakpoint]:
        path = str(Path(source.path).resolve()) if source.path else ""

        if path in self.breakpoints and not breakpoints and not lines:
            self.breakpoints.pop(path)
        elif path:
            self.breakpoints[path] = result = BreakpointsEntry(breakpoints or [], lines or [])
            return [
                Breakpoint(id=id(v), source=Source(path=path), verified=True, line=v.line) for v in result.breakpoints
            ]
        else:
            self._logger.error("not supported breakpoint")

        return []

    def process_state(self, source: Optional[str], line_no: Optional[int], type: Optional[str]) -> None:
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
            if len(self.stack_frames) <= self.stop_stack_len:
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
            if len(self.stack_frames) <= self.stop_stack_len:
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
            source = str(Path(source).resolve())
            if source in self.breakpoints:
                breakpoints = [v for v in self.breakpoints[source].breakpoints if v.line == line_no]
                if len(breakpoints) > 0:
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

    @_logger.call
    def wait_for_running(self) -> None:
        with self.condition:
            self.condition.wait_for(lambda: self.state in [State.Running, State.Stopped])

    def start_output_group(self, name: str, attributes: Dict[str, Any], type: Optional[str] = None) -> None:
        if self.group_output:
            source = attributes.get("source", None)
            line_no = attributes.get("lineno", None)

            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output=f"{(type +' ') if type else ''}{name}\n",
                        # category=OutputCategory.CONSOLE,
                        category="log",
                        group=OutputGroup.STARTCOLLAPSED,
                        source=Source(name=name, path=source) if source else None,
                        line=line_no,
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
                        # category=OutputCategory.CONSOLE,
                        category="log",
                        group=OutputGroup.END,
                        source=Source(name=name, path=source) if source else None,
                        line=line_no,
                    )
                ),
            )

    def add_stackframe_entry(
        self, name: str, type: str, source: Optional[str], line: Optional[int], column: Optional[int] = 1
    ) -> StackFrameEntry:
        from robot.running.context import EXECUTION_CONTEXTS

        if source is None or line is None or column is None:
            for v in self.stack_frames:
                if source is None:
                    source = v.source
                if line is None:
                    line = v.line
                if column is None:
                    column = v.column
                if source is not None and line is not None and column is not None:
                    break

        result = StackFrameEntry(
            weakref.ref(EXECUTION_CONTEXTS.current),
            name,
            type,
            source,
            line if line is not None else 0,
            column if column is not None else 0,
        )
        self.stack_frames.appendleft(result)

        return result

    def start_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        source = attributes.get("source", None)
        line_no = attributes.get("lineno", 1)
        longname = attributes.get("longname", "")
        type = "SUITE"

        entry = self.add_stackframe_entry(longname, type, source, line_no)

        self.process_state(entry.source, entry.line, entry.type)

        self.wait_for_running()

    def end_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        if self.stack_frames:
            self.stack_frames.popleft()

    def start_test(self, name: str, attributes: Dict[str, Any]) -> None:
        source = attributes.get("source", None)
        line_no = attributes.get("lineno", 1)
        longname = attributes.get("longname", "")
        type = "TEST"

        entry = self.add_stackframe_entry(longname, type, source, line_no)

        self.process_state(entry.source, entry.line, entry.type)

        self.wait_for_running()

    def end_test(self, name: str, attributes: Dict[str, Any]) -> None:
        if self.stack_frames:
            self.stack_frames.popleft()

    def start_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        status = attributes.get("status", "")

        if status == "NOT RUN":
            return

        source = attributes.get("source", None)
        line_no = attributes.get("lineno", 1)
        kwname = attributes.get("kwname", "")
        type = attributes.get("type", "KEYWORD")

        entry = self.add_stackframe_entry(kwname, type, source, line_no)

        self.process_state(entry.source, entry.line, entry.type)

        self.wait_for_running()

    def end_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        status = attributes.get("status", "")

        if status == "NOT RUN":
            return

        if self.stack_frames:
            self.stack_frames.popleft()

    def set_main_thread(self, thread: threading.Thread) -> None:
        self.main_thread = thread

    def get_threads(self) -> List[Thread]:
        main_thread = self.main_thread or threading.main_thread()

        return [Thread(id=main_thread.ident if main_thread.ident else 0, name=main_thread.name or "")]

    def get_stack_trace(
        self,
        thread_id: int,
        start_frame: Optional[int] = None,
        levels: Optional[int] = None,
        format: Optional[StackFrameFormat] = None,
    ) -> StackTraceResult:
        start_frame = start_frame or 0
        levels = start_frame + 1 + (levels or len(self.stack_frames))

        frames = [
            StackFrame(
                id=v.id,
                name=v.name,
                line=v.line,
                column=v.column,
                source=Source(path=v.source) if v.source is not None else None,
            )
            for v in itertools.islice(self.stack_frames, start_frame, levels)
        ]

        return StackTraceResult(frames, len(frames))

    def log_message(self, message: Dict[str, Any]) -> None:
        if self.output_log:
            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output="LOG> {timestamp} {level}: {message}\n".format(**message), category="log"
                    )
                ),
            )

    def message(self, message: Dict[str, Any]) -> None:
        if self.output_messages:
            self.send_event(
                self,
                OutputEvent(
                    body=OutputEventBody(
                        output="MSG> {timestamp} {level}: {message}\n".format(**message),
                        category=OutputCategory.CONSOLE,
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
                if context.variables._test is not None and context.variables._test != context.variables.current:
                    result.append(
                        Scope(
                            name="Test",
                            expensive=False,
                            presentation_hint="test",
                            variables_reference=entry.test_id(),
                        )
                    )
                if context.variables._suite is not None and context.variables._suite != context.variables.current:
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
        result: List[Variable] = []
        entry = next(
            (
                v
                for v in self.stack_frames
                if variables_reference in [v.global_id(), v.local_id(), v.suite_id(), v.test_id()]
            ),
            None,
        )
        if entry is not None:
            context = entry.context()
            if context is not None:

                if entry.global_id() == variables_reference:
                    result += [
                        Variable(name=k, value=repr(v), type=repr(type(v)))
                        for k, v in context.variables._global.as_dict().items()
                    ]
                elif entry.suite_id() == variables_reference:
                    # current_index = context.variables._scopes.index(context.variables._suite)
                    # globals = context.variables._scopes[max(current_index - 1, 0)].as_dict()
                    globals = context.variables._global.as_dict()
                    result += [
                        Variable(name=k, value=repr(v), type=repr(type(v)))
                        for k, v in context.variables._suite.as_dict().items()
                        if k not in globals or globals[k] != v
                    ]
                elif entry.test_id() == variables_reference:
                    # current_index = context.variables._scopes.index(context.variables._test)
                    # globals = context.variables._scopes[max(current_index - 1, 0)].as_dict()
                    globals = context.variables._suite.as_dict()
                    result += [
                        Variable(name=k, value=repr(v), type=repr(type(v)))
                        for k, v in context.variables._test.as_dict().items()
                        if k not in globals or globals[k] != v
                    ]
                elif entry.local_id() == variables_reference:
                    current_index = context.variables._scopes.index(context.variables.current)
                    globals = context.variables._scopes[max(current_index - 1, 0)].as_dict()
                    result += [
                        Variable(name=k, value=repr(v), type=repr(type(v)))
                        for k, v in context.variables.current.as_dict().items()
                        if k not in globals or globals[k] != v
                    ]

        return result

    VARS_RE = re.compile(r"^[$@&%]\{.*\}$")

    def evaluate(
        self,
        expression: str,
        frame_id: Optional[int] = None,
        context: Union[EvaluateArgumentContext, str, None] = None,
        format: Optional[ValueFormat] = None,
    ) -> EvaluateResult:
        from robot.running.context import EXECUTION_CONTEXTS
        from robot.variables.evaluation import evaluate_expression

        evaluate_context: Any = None

        if frame_id is not None:
            evaluate_context = (
                next((v.context() for v in self.stack_frames if v.id == frame_id), None)
                if frame_id is not None
                else None
            )

        if evaluate_context is None:
            evaluate_context = EXECUTION_CONTEXTS.current

        try:
            vars = evaluate_context.variables.current if frame_id is not None else evaluate_context.variables._global
            if self.VARS_RE.match(expression.strip()):
                result = vars.replace_string(expression)
            else:
                result = evaluate_expression(vars.replace_string(expression), vars.store)
        except BaseException as e:
            result = e

        return EvaluateResult(repr(result), repr(type(result)))
