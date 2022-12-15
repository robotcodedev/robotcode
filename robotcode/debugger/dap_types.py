from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Literal, Optional, Union

from ..utils.dataclasses import to_camel_case, to_snake_case


@dataclass
class Model:
    @classmethod
    def _encode_case(cls, s: str) -> str:
        return to_camel_case(s)

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return to_snake_case(s)


def __next_id_iter() -> Iterator[int]:
    i = 0
    while True:
        yield i
        i += 1


_next_id_iterator = __next_id_iter()


def _next_id() -> int:
    return next(_next_id_iterator)


@dataclass
class ProtocolMessage(Model):
    type: Union[Literal["request", "response", "event"], str]
    seq: int = field(default_factory=lambda: _next_id())


@dataclass
class _Request(Model):
    command: str
    arguments: Optional[Any] = None


@dataclass
class Request(ProtocolMessage, _Request):
    type: str = "request"


@dataclass
class _Event(Model):
    event: str


@dataclass
class Event(ProtocolMessage, _Event):
    type: str = "event"
    body: Optional[Any] = None


@dataclass
class _Response(Model):
    request_seq: int = field(metadata={"alias": "request_seq"})
    success: bool
    command: str
    message: Optional[Union[Literal["cancelled"], str]] = None


@dataclass
class Response(ProtocolMessage, _Response):
    type: str = "response"
    body: Optional[Any] = None


@dataclass
class Message(Model):
    format: str
    id: int = -1
    variables: Optional[Dict[str, str]] = None
    send_telemetry: Optional[bool] = None
    show_user: Optional[bool] = None
    url: Optional[str] = None
    url_label: Optional[str] = None

    def __str__(self) -> str:
        result = self.format

        for k, v in (self.variables or {}).items():
            result = result.replace(f"{{{k}}}", v)

        result += f" ({super().__str__()})"
        return result


@dataclass
class ErrorBody(Model):
    error: Optional[Message] = None


@dataclass
class _ErrorResponse(Model):
    body: Optional[ErrorBody]


@dataclass
class ErrorResponse(Response, _ErrorResponse):
    body: Optional[ErrorBody] = field()


@dataclass
class CancelArguments(Model):
    request_id: Optional[int] = None
    progress_id: Optional[int] = None


@dataclass
class CancelRequest(Request):
    arguments: Optional[CancelArguments] = None
    command: str = "cancel"


@dataclass
class CancelResponse(Response):
    pass


@dataclass
class InitializedEvent(Event):
    event: str = "initialized"


class StoppedReason(Enum):
    STEP = "step"
    BREAKPOINT = "breakpoint"
    EXCEPTION = "exception"
    PAUSE = "pause"
    ENTRY = "entry"
    GOTO = "goto"
    FUNCTION_BREAKPOINT = "function breakpoint"
    DATA_BREAKPOINT = "data breakpoint"
    INSTRUCTION_BREAKPOINT = "instruction breakpoint"

    def __repr__(self) -> str:  # pragma: no cover
        return super().__str__()


@dataclass
class StoppedEventBody(Model):
    reason: Union[
        StoppedReason,
        str,
    ]
    description: Optional[str] = None
    thread_id: Optional[int] = None
    preserve_focus_hint: Optional[bool] = None
    text: Optional[str] = None
    all_threads_stopped: Optional[bool] = None
    hit_breakpoint_ids: Optional[List[int]] = None


@dataclass
class _StoppedEvent(Model):
    body: StoppedEventBody


@dataclass
class StoppedEvent(Event, _StoppedEvent):
    body: StoppedEventBody = field()
    event: str = "stopped"


@dataclass
class ContinuedEventBody(Model):
    thread_id: int
    all_threads_continued: Optional[bool]


@dataclass
class _ContinuedEvent(Model):
    body: ContinuedEventBody


@dataclass
class ContinuedEvent(Event, _ContinuedEvent):
    body: ContinuedEventBody = field()
    event: str = "continued"


@dataclass
class ExitedEventBody(Model):
    exit_code: int


@dataclass
class _ExitedEvent(Model):
    body: ExitedEventBody


@dataclass
class ExitedEvent(Event, _ExitedEvent):
    body: ExitedEventBody = field()
    event: str = "exited"


@dataclass
class TerminatedEventBody(Model):
    restart: Optional[Any] = None


@dataclass
class _TerminatedEvent(Model):
    body: Optional[TerminatedEventBody] = None


@dataclass
class TerminatedEvent(Event, _TerminatedEvent):
    body: Optional[TerminatedEventBody] = None
    event: str = "terminated"


class ChecksumAlgorithm(Enum):
    MD5 = "MD5"
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    TIMESTAMP = "timestamp"

    def __repr__(self) -> str:  # pragma: no cover
        return super().__str__()


@dataclass
class Checksum(Model):
    algorithm: ChecksumAlgorithm
    checksum: str


@dataclass
class Source(Model):
    name: Optional[str] = None
    path: Optional[str] = None
    source_reference: Optional[int] = None
    presentation_hint: Optional[Literal["normal", "emphasize", "deemphasize"]] = None
    origin: Optional[str] = None
    sources: Optional[List[Source]] = None
    adapter_data: Optional[Any] = None
    checksums: Optional[List[Checksum]] = None


class OutputCategory(Enum):
    CONSOLE = "console"
    IMPORTANT = "important"
    STDOUT = "stdout"
    STDERR = "stderr"
    TELEMETRY = "telemetry"

    def __repr__(self) -> str:  # pragma: no cover
        return super().__str__()


class OutputGroup(Enum):
    START = "start"
    STARTCOLLAPSED = "startCollapsed"
    END = "end"

    def __repr__(self) -> str:  # pragma: no cover
        return super().__str__()


@dataclass
class OutputEventBody(Model):
    output: str
    category: Union[OutputCategory, str, None] = None
    group: Optional[OutputGroup] = None
    variables_reference: Optional[int] = None
    source: Optional[Source] = None
    line: Optional[int] = None
    column: Optional[int] = None
    data: Optional[Any] = None


@dataclass
class _OutputEvent(Model):
    body: Optional[OutputEventBody] = None


@dataclass
class OutputEvent(Event, _OutputEvent):
    body: Optional[OutputEventBody] = None
    event: str = "output"


@dataclass
class InitializeRequestArguments(Model):
    adapter_id: str = field(metadata={"alias": "adapterID"})
    client_id: Optional[str] = field(metadata={"alias": "clientID"})
    client_name: Optional[str] = None
    locale: Optional[str] = None
    lines_start_at1: Optional[bool] = None
    columns_start_at1: Optional[bool] = None
    path_format: Optional[Union[Literal["path", "uri"], str]] = None
    supports_variable_type: Optional[bool] = None
    supports_variable_paging: Optional[bool] = None
    supports_run_in_terminal_request: Optional[bool] = None
    supports_memory_references: Optional[bool] = None
    supports_progress_reporting: Optional[bool] = None
    supports_invalidated_event: Optional[bool] = None


@dataclass
class _InitializeRequest(Model):
    arguments: InitializeRequestArguments


@dataclass
class InitializeRequest(Request, _InitializeRequest):
    arguments: InitializeRequestArguments = field()
    command: str = "initialize"


@dataclass
class AttachRequestArguments(Model):
    restart: Optional[Any] = field(default=None, metadata={"alias": "__restart"})


@dataclass
class _AttachRequest(Model):
    arguments: AttachRequestArguments


@dataclass
class AttachRequest(Request, _AttachRequest):
    arguments: AttachRequestArguments = field()
    command: str = "attach"


@dataclass
class AttachResponse(Response):
    pass


@dataclass
class ExceptionBreakpointsFilter(Model):
    filter: str
    label: str
    description: Optional[str] = None
    default: Optional[bool] = None
    supports_condition: Optional[bool] = None
    condition_description: Optional[str] = None


@dataclass
class ColumnDescriptor(Model):
    attribute_name: str
    label: str
    format: Optional[str] = None
    type: Optional[Literal["string", "number", "boolean", "unixTimestampUTC"]] = None
    width: Optional[int] = None


@dataclass
class Capabilities(Model):
    supports_configuration_done_request: Optional[bool] = None
    supports_function_breakpoints: Optional[bool] = None
    supports_conditional_breakpoints: Optional[bool] = None
    supports_hit_conditional_breakpoints: Optional[bool] = None
    supports_evaluate_for_hovers: Optional[bool] = None
    exception_breakpoint_filters: Optional[List[ExceptionBreakpointsFilter]] = None
    supports_step_back: Optional[bool] = None
    supports_set_variable: Optional[bool] = None
    supports_restart_frame: Optional[bool] = None
    supports_goto_targets_request: Optional[bool] = None
    supports_step_in_targets_request: Optional[bool] = None
    supports_completions_request: Optional[bool] = None
    completion_trigger_characters: Optional[List[str]] = None
    supports_modules_request: Optional[bool] = None
    additional_module_columns: Optional[List[ColumnDescriptor]] = None
    supported_checksum_algorithms: Optional[List[ChecksumAlgorithm]] = None
    supports_restart_request: Optional[bool] = None
    supports_exception_options: Optional[bool] = None
    supports_value_formatting_options: Optional[bool] = None
    supports_exception_info_request: Optional[bool] = None
    support_terminate_debuggee: Optional[bool] = None
    support_suspend_debuggee: Optional[bool] = None
    supports_delayed_stack_trace_loading: Optional[bool] = None
    supports_loaded_sources_request: Optional[bool] = None
    supports_log_points: Optional[bool] = None
    supports_terminate_threads_request: Optional[bool] = None
    supports_set_expression: Optional[bool] = None
    supports_terminate_request: Optional[bool] = None
    supports_data_breakpoints: Optional[bool] = None
    supports_read_memory_request: Optional[bool] = None
    supports_disassemble_request: Optional[bool] = None
    supports_cancel_request: Optional[bool] = None
    supports_breakpoint_locations_request: Optional[bool] = None
    supports_clipboard_context: Optional[bool] = None
    supports_stepping_granularity: Optional[bool] = None
    supports_instruction_breakpoints: Optional[bool] = None
    supports_exception_filter_options: Optional[bool] = None


@dataclass
class InitializeResponse(Response):
    body: Optional[Capabilities] = None


@dataclass
class LaunchRequestArguments(Model):
    no_debug: Optional[bool] = None
    restart: Optional[Any] = field(default=None, metadata={"alias": "__restart"})


@dataclass
class _LaunchRequest(Model):
    arguments: LaunchRequestArguments


@dataclass
class LaunchRequest(Request, _LaunchRequest):
    arguments: LaunchRequestArguments = field()
    command: str = "launch"


@dataclass
class LaunchResponse(Response):
    pass


class RunInTerminalKind(Enum):
    INTEGRATED = "integrated"
    EXTERNAL = "external"

    def __repr__(self) -> str:  # pragma: no cover
        return super().__str__()


@dataclass
class RunInTerminalRequestArguments(Model):
    cwd: str
    args: List[str]
    env: Optional[Dict[str, Optional[str]]] = None
    kind: Optional[RunInTerminalKind] = None
    title: Optional[str] = None
    args_can_be_interpreted_by_shell: Optional[bool] = None


@dataclass
class _RunInTerminalRequest(Model):
    arguments: RunInTerminalRequestArguments


@dataclass
class RunInTerminalRequest(Request, _RunInTerminalRequest):
    arguments: RunInTerminalRequestArguments = field()
    command: str = field(default="runInTerminal", init=False, metadata={"force_json": True})


@dataclass
class RunInTerminalResponseBody(Model):
    process_id: Optional[int] = None
    shell_process_id: Optional[int] = None


@dataclass
class _RunInTerminalResponse(Model):
    body: RunInTerminalResponseBody


@dataclass
class RunInTerminalResponse(Response, _RunInTerminalResponse):
    body: RunInTerminalResponseBody = field()


@dataclass
class ConfigurationDoneArguments(Model):
    pass


@dataclass
class _ConfigurationDoneRequest(Model):
    arguments: Optional[ConfigurationDoneArguments] = None


@dataclass
class ConfigurationDoneRequest(Request, _ConfigurationDoneRequest):
    arguments: Optional[ConfigurationDoneArguments] = None
    command: str = "configurationDone"


@dataclass
class ConfigurationDoneResponse(Response):
    pass


@dataclass
class DisconnectArguments(Model):
    restart: Optional[bool] = None
    terminate_debuggee: Optional[bool] = None
    suspend_debuggee: Optional[bool] = None


@dataclass
class _DisconnectRequest(Model):
    arguments: Optional[DisconnectArguments] = None


@dataclass
class DisconnectRequest(Request, _DisconnectRequest):
    arguments: Optional[DisconnectArguments] = None
    command: str = "disconnect"


@dataclass
class DisconnectResponse(Response):
    pass


@dataclass
class SourceBreakpoint(Model):
    line: int
    column: Optional[int] = None
    condition: Optional[str] = None
    hit_condition: Optional[str] = None
    log_message: Optional[str] = None


@dataclass
class SetBreakpointsArguments(Model):
    source: Source
    breakpoints: Optional[List[SourceBreakpoint]] = None
    lines: Optional[List[int]] = None
    source_modified: Optional[bool] = None


@dataclass
class _SetBreakpointsRequest(Model):
    arguments: SetBreakpointsArguments


@dataclass
class SetBreakpointsRequest(Request, _SetBreakpointsRequest):
    arguments: SetBreakpointsArguments = field()
    command: str = "setBreakpoints"


@dataclass
class Breakpoint(Model):
    verified: bool
    id: Optional[int] = None
    message: Optional[str] = None
    source: Optional[Source] = None
    line: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    instruction_reference: Optional[str] = None
    offset: Optional[int] = None


@dataclass
class SetBreakpointsResponseBody(Model):
    breakpoints: List[Breakpoint]


@dataclass
class _SetBreakpointsResponse(Model):
    body: SetBreakpointsResponseBody


@dataclass
class SetBreakpointsResponse(Response, _SetBreakpointsResponse):
    body: SetBreakpointsResponseBody = field()


@dataclass
class ThreadsRequest(Request):
    command: str = "threads"


@dataclass
class Thread(Model):
    id: int
    name: str


@dataclass
class ThreadsResponseBody(Model):
    threads: List[Thread]


@dataclass
class _ThreadsResponse(Model):
    body: ThreadsResponseBody


@dataclass
class ThreadsResponse(Response, _ThreadsResponse):
    body: ThreadsResponseBody = field()


@dataclass
class TerminateArguments(Model):
    restart: Optional[bool] = None


@dataclass
class _TerminateRequest(Model):
    arguments: Optional[TerminateArguments] = None


@dataclass
class TerminateRequest(Request, _TerminateRequest):
    arguments: Optional[TerminateArguments] = None
    command: str = "terminate"


@dataclass
class TerminateResponse(Response):
    pass


@dataclass
class StackFrameFormat(Model):
    parameters: Optional[bool] = None
    parameter_types: Optional[bool] = None
    parameter_names: Optional[bool] = None
    parameter_values: Optional[bool] = None
    line: Optional[bool] = None
    module: Optional[bool] = None
    include_all: Optional[bool] = None


@dataclass
class StackTraceArguments(Model):
    thread_id: int
    start_frame: Optional[int] = None
    levels: Optional[int] = None
    format: Optional[StackFrameFormat] = None


@dataclass
class _StackTraceRequest(Model):
    arguments: StackTraceArguments


@dataclass
class StackTraceRequest(Request, _StackTraceRequest):
    arguments: StackTraceArguments = field()
    command: str = "stackTrace"


@dataclass
class StackFrame(Model):
    id: int
    name: str
    line: int
    column: int
    source: Optional[Source] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    can_restart: Optional[bool] = None
    instruction_pointer_reference: Optional[str] = None
    module_id: Union[int, str, None] = None
    presentation_hint: Optional[Literal["normal", "label", "subtle"]] = None


@dataclass
class StackTraceResponseBody(Model):
    stack_frames: List[StackFrame]
    total_frames: Optional[int]


@dataclass
class _StackTraceResponse(Model):
    body: StackTraceResponseBody


@dataclass
class StackTraceResponse(Response, _StackTraceResponse):
    body: StackTraceResponseBody = field()


@dataclass
class ScopesArguments(Model):
    frame_id: int


@dataclass
class Scope(Model):
    name: str
    variables_reference: int
    expensive: bool
    presentation_hint: Union[Literal["arguments", "locals", "registers"], str, None] = None
    named_variables: Optional[int] = None
    indexed_variables: Optional[int] = None
    source: Optional[Source] = None
    line: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None


@dataclass
class _ScopesRequest(Model):
    arguments: ScopesArguments


@dataclass
class ScopesRequest(Request, _ScopesRequest):
    arguments: ScopesArguments = field()
    command: str = "scopes"


@dataclass
class ScopesResponseBody(Model):
    scopes: List[Scope]


@dataclass
class _ScopesResponse(Model):
    body: ScopesResponseBody


@dataclass
class ScopesResponse(Response, _ScopesResponse):
    body: ScopesResponseBody = field()


@dataclass
class ContinueArguments(Model):
    thread_id: int


@dataclass
class _ContinueRequest(Model):
    arguments: ContinueArguments


@dataclass
class ContinueRequest(Request, _ContinueRequest):
    arguments: ContinueArguments = field()
    command: str = "continue"


@dataclass
class ContinueResponseBody(Model):
    all_threads_continued: Optional[bool] = None


@dataclass
class _ContinueResponse(Model):
    body: ContinueResponseBody


@dataclass
class ContinueResponse(Response, _ContinueResponse):
    body: ContinueResponseBody = field()


@dataclass
class PauseArguments(Model):
    thread_id: int


@dataclass
class _PauseRequest(Model):
    arguments: PauseArguments


@dataclass
class PauseRequest(Request, _PauseRequest):
    arguments: PauseArguments = field()
    command: str = "pause"


@dataclass
class PauseResponse(Response):
    pass


@dataclass
class SteppingGranularity(Enum):
    STATEMENT = "statement"
    LINE = "line"
    INSTRUCTION = "instruction"

    def __repr__(self) -> str:  # pragma: no cover
        return super().__str__()


@dataclass
class NextArguments(Model):
    thread_id: int
    granularity: Optional[SteppingGranularity] = None


@dataclass
class _NextRequest(Model):
    arguments: NextArguments


@dataclass
class NextRequest(Request, _NextRequest):
    arguments: NextArguments = field()
    command: str = "next"


@dataclass
class NextResponse(Response):
    pass


@dataclass
class StepInArguments(Model):
    thread_id: int
    target_id: Optional[int] = None
    granularity: Optional[SteppingGranularity] = None


@dataclass
class _StepInRequest(Model):
    arguments: StepInArguments


@dataclass
class StepInRequest(Request, _StepInRequest):
    arguments: StepInArguments = field()
    command: str = "stepIn"


@dataclass
class StepInResponse(Response):
    pass


@dataclass
class StepOutArguments(Model):
    thread_id: int
    granularity: Optional[SteppingGranularity] = None


@dataclass
class _StepOutRequest(Model):
    arguments: StepOutArguments


@dataclass
class StepOutRequest(Request, _StepOutRequest):
    arguments: StepOutArguments = field()
    command: str = "stepOut"


@dataclass
class StepOutResponse(Response):
    pass


@dataclass
class ValueFormat(Model):
    hex: Optional[bool] = None


@dataclass
class VariablesArguments(Model):
    variables_reference: int
    filter: Optional[Literal["indexed", "named"]] = None
    start: Optional[int] = None
    count: Optional[int] = None
    format: Optional[ValueFormat] = None


@dataclass
class _VariablesRequest(Model):
    arguments: VariablesArguments


@dataclass
class VariablesRequest(Request, _VariablesRequest):
    arguments: VariablesArguments = field()
    command: str = "variables"


@dataclass
class VariablePresentationHint(Model):
    kind: Union[
        Literal[
            "property",
            "method",
            "class",
            "data",
            "event",
            "baseClass",
            "innerClass",
            "interface",
            "mostDerivedClass",
            "virtual",
            "dataBreakpoint",
        ],
        str,
        None,
    ] = None

    attributes: Optional[
        List[
            Union[
                Literal[
                    "static",
                    "constant",
                    "readOnly",
                    "rawString",
                    "hasObjectId",
                    "canHaveObjectId",
                    "hasSideEffects",
                    "hasDataBreakpoint",
                ],
                str,
            ]
        ]
    ] = None

    visibility: Union[Literal["public", "private", "protected", "internal", "final"], str, None] = None


@dataclass
class Variable(Model):
    name: str
    value: str
    type: Optional[str] = None
    presentation_hint: Optional[VariablePresentationHint] = None
    evaluate_name: Optional[str] = None
    variables_reference: int = 0
    named_variables: Optional[int] = None
    indexed_variables: Optional[int] = None
    memory_reference: Optional[str] = None


@dataclass
class VariablesResponseBody(Model):
    variables: List[Variable]


@dataclass
class _VariablesResponse(Model):
    body: VariablesResponseBody


@dataclass
class VariablesResponse(Response, _VariablesResponse):
    body: VariablesResponseBody = field()


class EvaluateArgumentContext(Enum):
    WATCH = "watch"
    REPL = "repl"
    HOVER = "hover"
    CLIPBOARD = "clipboard"

    def __repr__(self) -> str:  # pragma: no cover
        return super().__str__()


@dataclass
class EvaluateArguments(Model):
    expression: str
    frame_id: Optional[int] = None
    context: Union[EvaluateArgumentContext, str, None] = None
    format: Optional[ValueFormat] = None


@dataclass
class _EvaluateRequest(Model):
    arguments: EvaluateArguments


@dataclass
class EvaluateRequest(Request, _EvaluateRequest):
    arguments: EvaluateArguments = field()
    command: str = "evaluate"


@dataclass
class EvaluateResponseBody(Model):
    result: str
    type: Optional[str] = None
    presentation_hint: Optional[VariablePresentationHint] = None
    variables_reference: int = 0
    named_variables: Optional[int] = None
    indexed_variables: Optional[int] = None
    memory_reference: Optional[str] = None


@dataclass
class _EvaluateResponse(Model):
    body: VariablesResponseBody


@dataclass
class EvaluateResponse(Response, _EvaluateResponse):
    body: VariablesResponseBody = field()


@dataclass
class SetVariableArguments(Model):
    variables_reference: int
    name: str
    value: str
    format: Optional[ValueFormat] = None


@dataclass
class _SetVariableRequest(Model):
    arguments: SetVariableArguments


@dataclass
class SetVariableRequest(Request, _SetVariableRequest):
    arguments: SetVariableArguments = field()
    command: str = "setVariable"


@dataclass
class SetVariableResponseBody(Model):
    value: str
    type: Optional[str]
    variables_reference: Optional[int] = None
    named_variables: Optional[int] = None
    indexed_variables: Optional[int] = None


@dataclass
class _SetVariableResponse(Model):
    body: SetVariableResponseBody


@dataclass
class SetVariableResponse(Response, _SetVariableResponse):
    body: SetVariableResponseBody = field()


@dataclass(unsafe_hash=True)
class ExceptionFilterOptions(Model):
    filter_id: str
    condition: Optional[str] = None


class ExceptionBreakMode(Enum):
    NEVER = "never"
    ALWAYS = "always"
    UNHANDLED = "unhandled"
    USER_UNHANDLED = "userUnhandled"

    def __repr__(self) -> str:  # pragma: no cover
        return super().__str__()


@dataclass
class ExceptionPathSegment(Model):
    names: List[str]
    negate: Optional[bool] = None


@dataclass
class ExceptionOptions(Model):
    break_mode: ExceptionBreakMode
    path: Optional[List[ExceptionPathSegment]] = None


@dataclass
class SetExceptionBreakpointsArguments(Model):
    filters: List[str]
    filter_options: Optional[List[ExceptionFilterOptions]] = None
    exception_options: Optional[List[ExceptionOptions]] = None


@dataclass
class _SetExceptionBreakpointsRequest(Model):
    arguments: SetExceptionBreakpointsArguments


@dataclass
class SetExceptionBreakpointsRequest(Request, _SetExceptionBreakpointsRequest):
    arguments: SetExceptionBreakpointsArguments = field()
    command: str = "setExceptionBreakpoints"


@dataclass
class SetExceptionBreakpointsResponseBody(Model):
    breakpoints: Optional[List[Breakpoint]] = None


@dataclass
class SetExceptionBreakpointsResponse(Response):
    body: Optional[SetExceptionBreakpointsResponseBody] = None
