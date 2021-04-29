from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, Iterator, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class Model(BaseModel):
    class Config:
        allow_population_by_field_name = True
        # use_enum_values = True

        @classmethod
        def alias_generator(cls, string: str) -> str:
            string = re.sub(r"^[\-_\.]", "", str(string))
            if not string:
                return string
            return str(string[0]).lower() + re.sub(
                r"[\-_\.\s]([a-z])",
                lambda matched: str(matched.group(1)).upper(),
                string[1:],
            )


def __next_id_iter() -> Iterator[int]:
    i = 0
    while True:
        yield i
        i += 1


_next_id_iterator = __next_id_iter()


def _next_id() -> int:
    return next(_next_id_iterator)


class ProtocolMessage(Model):
    seq: int = Field(default_factory=lambda: _next_id())
    type: Union[Literal["request", "response", "event"], str]


class Request(ProtocolMessage):
    type: str = Field("request", const=True)
    command: str
    arguments: Optional[Any] = None


class Event(ProtocolMessage):
    type: str = Field("event", const=True)
    event: str
    body: Optional[Any] = None


class Response(ProtocolMessage):
    # seq: int = Field(-1, const=True)
    type: str = Field(
        "response",
        const=True,
    )
    request_seq: int = Field(..., alias="request_seq")
    success: bool
    command: str
    message: Optional[Union[Literal["cancelled"], str]]
    body: Optional[Any] = None


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


class ErrorBody(Model):
    error: Optional[Message] = None


class ErrorResponse(Response):
    body: Optional[ErrorBody]


class CancelArguments(Model):
    request_id: Optional[int] = None
    progress_id: Optional[int] = None


class CancelRequest(Request):
    command: str = Field("cancel", const=True)
    arguments: Optional[CancelArguments] = None


class CancelResponse(Response):
    pass


class InitializedEvent(Event):
    event: str = Field("initialized", const=True)


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


class StoppedEvent(Event):
    event: str = Field("stopped", const=True)
    body: StoppedEventBody


class ContinuedEventBody(Model):
    thread_id: int
    all_threads_continued: Optional[bool]


class ContinuedEvent(Event):
    event: str = Field("continued", const=True)
    body: ContinuedEventBody


class ExitedEventBody(Model):
    exit_code: int


class ExitedEvent(Event):
    event: str = Field("exited", const=True)
    body: ExitedEventBody


class TerminatedEventBody(Model):
    restart: Optional[Any] = None


class TerminatedEvent(Event):
    event: str = Field("terminated", const=True)
    body: Optional[TerminatedEventBody] = None


class OutputCategory(Enum):
    CONSOLE = "console"
    STDOUT = "stdout"
    STDERR = "stderr"
    TELEMETRY = "telemetry"


class OutputGroup(Enum):
    START = "start"
    STARTCOLLAPSED = "startCollapsed"
    END = "end"


class OutputEventBody(Model):
    output: str
    category: Union[OutputCategory, str, None] = None
    group: Optional[OutputGroup] = None
    variables_reference: Optional[int] = None
    source: Optional[Source] = None
    line: Optional[int] = None
    column: Optional[int] = None
    data: Optional[Any] = None


class OutputEvent(Event):
    event: str = Field("output", const=True)
    body: Optional[OutputEventBody] = None


class InitializeRequestArguments(Model):
    adapter_id: str = Field(..., alias="adapterID")
    client_id: Optional[str] = Field(None, alias="clientID")
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


class InitializeRequest(Request):
    command: str = Field("initialize", const=True)
    arguments: InitializeRequestArguments


class ExceptionBreakpointsFilter(Model):
    filter: str
    label: str
    description: Optional[str] = None
    default: Optional[bool] = None
    supports_condition: Optional[bool] = None
    condition_description: Optional[str] = None


class ColumnDescriptor(Model):
    attribute_name: str
    label: str
    format: Optional[str] = None
    type: Optional[Literal["string", "number", "boolean", "unixTimestampUTC"]] = None
    width: Optional[int] = None


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


class InitializeResponse(Response):
    body: Optional[Capabilities] = None


class LaunchRequestArguments(Model):
    no_debug: Optional[bool] = None
    restart: Optional[Any] = Field(None, alias="__restart")


class LaunchRequest(Request):
    command: str = Field("launch", const=True)
    arguments: LaunchRequestArguments


class LaunchResponse(Response):
    pass


class RunInTerminalKind(Enum):
    INTEGRATED = "integrated"
    EXTERNAL = "external"


class RunInTerminalRequestArguments(Model):
    cwd: str
    args: List[str]
    env: Optional[Dict[str, Optional[str]]] = None
    kind: Optional[RunInTerminalKind] = None
    title: Optional[str] = None


class RunInTerminalRequest(Request):
    command: str = Field("runInTerminal", const=True)
    arguments: RunInTerminalRequestArguments


class RunInTerminalResponseBody(Model):
    process_id: Optional[int] = None
    shell_process_id: Optional[int] = None


class RunInTerminalResponse(Response):
    body: RunInTerminalResponseBody


class ConfigurationDoneArguments(Model):
    pass


class ConfigurationDoneRequest(Request):
    command: str = Field("configurationDone", const=True)
    arguments: Optional[ConfigurationDoneArguments] = None


class ConfigurationDoneResponse(Response):
    pass


class DisconnectArguments(Model):
    restart: Optional[bool] = None
    terminate_debuggee: Optional[bool] = None
    suspend_debuggee: Optional[bool] = None


class DisconnectRequest(Request):
    command: str = Field("disconnect", const=True)
    arguments: Optional[DisconnectArguments] = None


class DisconnectResponse(Response):
    pass


class ChecksumAlgorithm(Enum):
    MD5 = "MD5"
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    TIMESTAMP = "timestamp"


class Checksum(BaseModel):
    algorithm: ChecksumAlgorithm
    checksum: str


class Source(Model):
    name: Optional[str] = None
    path: Optional[str] = None
    source_reference: Optional[int] = None
    presentation_hint: Optional[Literal["normal", "emphasize", "deemphasize"]] = None
    origin: Optional[str] = None
    sources: Optional[List[Source]] = None
    adapter_data: Optional[Any] = None
    checksums: Optional[List[Checksum]] = None


class SourceBreakpoint(Model):
    line: int
    column: Optional[int] = None
    condition: Optional[str] = None
    hit_condition: Optional[str] = None
    log_message: Optional[str] = None


class SetBreakpointsArguments(Model):
    source: Source
    breakpoints: Optional[List[SourceBreakpoint]] = None
    lines: Optional[List[int]] = None
    source_modified: Optional[bool] = None


class SetBreakpointsRequest(Request):
    command: str = Field("setBreakpoints", const=True)
    arguments: SetBreakpointsArguments


class Breakpoint(Model):
    id: Optional[int] = None
    verified: bool
    message: Optional[str] = None
    source: Optional[Source] = None
    line: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    instruction_reference: Optional[str] = None
    offset: Optional[int] = None


class SetBreakpointsResponseBody(Model):
    breakpoints: List[Breakpoint]


class SetBreakpointsResponse(Response):
    body: SetBreakpointsResponseBody


class ThreadsRequest(Request):
    command: str = Field("threads", const=True)


class Thread(Model):
    id: int
    name: str


class ThreadsResponseBody(Model):
    threads: List[Thread]


class ThreadsResponse(Response):
    body: ThreadsResponseBody


class TerminateArguments(Model):
    restart: Optional[bool] = None


class TerminateRequest(Request):
    command: str = Field("terminate", const=True)
    arguments: Optional[TerminateArguments] = None


class TerminateResponse(Response):
    pass


class StackFrameFormat(Model):
    parameters: Optional[bool] = None
    parameter_types: Optional[bool] = None
    parameter_names: Optional[bool] = None
    parameter_values: Optional[bool] = None
    line: Optional[bool] = None
    module: Optional[bool] = None
    include_all: Optional[bool] = None


class StackTraceArguments(Model):
    thread_id: int
    start_frame: Optional[int] = None
    levels: Optional[int] = None
    format: Optional[StackFrameFormat] = None


class StackTraceRequest(Request):
    command: str = Field("stackTrace", const=True)
    arguments: StackTraceArguments


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


class StackTraceResponseBody(Model):
    stack_frames: List[StackFrame]
    total_frames: Optional[int]


class StackTraceResponse(Response):
    body: StackTraceResponseBody


class ScopesArguments(Model):
    frame_id: int


class Scope(Model):
    name: str
    presentation_hint: Union[Literal["arguments", "locals", "registers"], str, None] = None
    variables_reference: int
    named_variables: Optional[int] = None
    indexed_variables: Optional[int] = None
    expensive: bool
    source: Optional[Source] = None
    line: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None


class ScopesRequest(Request):
    command: str = Field("scopes", const=True)
    arguments: ScopesArguments


class ScopesResponseBody(Model):
    scopes: List[Scope]


class ScopesResponse(Response):
    body: ScopesResponseBody


class ContinueArguments(Model):
    thread_id: int


class ContinueRequest(Request):
    command: str = Field("continue", const=True)
    arguments: ContinueArguments


class ContinueResponseBody(Model):
    all_threads_continued: Optional[bool] = None


class ContinueResponse(Response):
    body: ContinueResponseBody


class PauseArguments(Model):
    thread_id: int


class PauseRequest(Request):
    command: str = Field("pause", const=True)
    arguments: PauseArguments


class PauseResponse(Response):
    pass


class SteppingGranularity(Enum):
    STATEMENT = "statement"
    LINE = "line"
    INSTRUCTION = "instruction"


class NextArguments(Model):
    thread_id: int
    granularity: Optional[SteppingGranularity] = None


class NextRequest(Request):
    command: str = Field("next", const=True)
    arguments: NextArguments


class NextResponse(Response):
    pass


class StepInArguments(Model):
    thread_id: int
    target_id: Optional[int] = None
    granularity: Optional[SteppingGranularity] = None


class StepInRequest(Request):
    command: str = Field("stepIn", const=True)
    arguments: StepInArguments


class StepInResponse(Response):
    pass


class StepOutArguments(Model):
    thread_id: int
    granularity: Optional[SteppingGranularity] = None


class StepOutRequest(Request):
    command: str = Field("stepOut", const=True)
    arguments: StepOutArguments


class StepOutResponse(Response):
    pass


class ValueFormat(Model):
    hex: Optional[bool] = None


class VariablesArguments(Model):
    variables_reference: int
    filter: Optional[Literal["indexed", "named"]] = None
    start: Optional[int] = None
    count: Optional[int] = None
    format: Optional[ValueFormat] = None


class VariablesRequest(Request):
    command: str = Field("variables", const=True)
    arguments: VariablesArguments


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


class VariablesResponseBody(Model):
    variables: List[Variable]


class VariablesResponse(Response):
    body: VariablesResponseBody
