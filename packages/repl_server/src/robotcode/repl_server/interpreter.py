import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Iterator, List, Optional, Protocol, Union, runtime_checkable

from robot.running import Keyword
from robot.utils.markuputils import html_format
from robot.utils.robottime import elapsed_time_to_string

from robotcode.core.utils.dataclasses import as_json
from robotcode.repl.base_interpreter import BaseInterpreter, is_true
from robotcode.robot.utils import get_robot_version

if TYPE_CHECKING:
    from robot import result, running


@dataclass
class ExecutionOutput:
    mime: str
    data: str


@dataclass
class ExecutionResult:
    success: Optional[bool] = None
    items: Optional[List[ExecutionOutput]] = None


class CellInputError(Exception):
    pass


@dataclass
class ResultData:
    pass


@dataclass
class MessageData(ResultData):
    id: str
    message: str
    level: str
    html: bool
    timestamp: Optional[str] = None

    node_type: str = "message"


@dataclass
class RootResultData(ResultData):
    items: List[ResultData] = field(default_factory=list)

    node_type: str = "root"


@runtime_checkable
class ResultDataWithChildren(Protocol):
    items: List[ResultData]


@dataclass
class KeywordResultData(ResultData):
    id: str
    name: str
    owner: str
    source_name: str
    doc: str
    args: List[str]
    assign: List[str]
    tags: List[str]
    timeout: Optional[str]
    type: str
    status: str
    message: str
    start_time: Optional[str]
    end_time: Optional[str]
    elapsed_time: Optional[str]

    items: List[ResultData] = field(default_factory=list)

    node_type: str = "keyword"


if get_robot_version() < (7, 0):

    def make_elapsed_time_str(elapsed_time: Union[timedelta, int, float, None]) -> Optional[str]:
        if elapsed_time is None:
            return None
        return str(elapsed_time_to_string(elapsed_time))

else:

    def make_elapsed_time_str(elapsed_time: Union[timedelta, int, float, None]) -> Optional[str]:
        if elapsed_time is None:
            return None
        return str(elapsed_time_to_string(elapsed_time, seconds=True))


class Interpreter(BaseInterpreter):
    def __init__(
        self,
        files: Optional[List[Path]] = None,
    ) -> None:
        super().__init__()
        self.files = files
        self.has_input = Event()
        self.executed = Event()
        self.no_execution = Event()
        self.no_execution.set()
        self._code: List[str] = []
        self._success: Optional[bool] = None
        self._result_data: Optional[ResultData] = None
        self._result_data_stack: List[ResultData] = []
        self.collect_messages: bool = False
        self._interrupted = False
        self._has_shutdown = False
        self._cell_errors: List[str] = []

    def shutdown(self) -> None:
        self._code = []
        self._has_shutdown = True
        self.has_input.set()

    def execute(self, source: str) -> ExecutionResult:
        self.no_execution.wait()

        self.no_execution.clear()

        self._result_data_stack = []

        self._success = None
        try:
            self._cell_errors = []
            self._interrupted = False

            self._result_data = RootResultData()

            self.executed.clear()

            self._code.append(source)
            self.has_input.set()

            self.executed.wait()

            return ExecutionResult(
                self._success,
                (
                    [
                        ExecutionOutput(
                            "x-application/robotframework-repl-log", as_json(self._result_data, compact=True)
                        ),
                        *(
                            [ExecutionOutput("application/vnd.code.notebook.stderr", "\n".join(self._cell_errors))]
                            if self._cell_errors
                            else []
                        ),
                    ]
                    if self._success is not None
                    else (
                        [ExecutionOutput("application/vnd.code.notebook.stderr", "\n".join(self._cell_errors))]
                        if self._cell_errors
                        else []
                    )
                ),
            )
        except BaseException as e:
            return ExecutionResult(False, [ExecutionOutput("application/vnd.code.notebook.stderr", str(e))])
        finally:
            self.no_execution.set()

    def get_input(self) -> Iterator[Optional[Keyword]]:
        while self._code:
            s = self._code.pop(0)
            test, errors = self.get_test_body_from_string(s)
            if errors:
                self._cell_errors.append(
                    "CellInputError: " + ("\n" + textwrap.indent("\n".join(errors), "    "))
                    if len(errors) > 1
                    else errors[0]
                )
                # raise CellInputError(errors)

            for kw in test.body:
                yield kw

    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        if self._result_data is not None and isinstance(self._result_data, ResultDataWithChildren):
            self._result_data.items.append(
                MessageData(
                    id=f"message-{len(self._result_data.items)}",
                    message=message,
                    level=level,
                    html=is_true(html),
                    timestamp=timestamp.strftime("%H:%M:%S") if isinstance(timestamp, datetime) else str(timestamp),
                )
            )

    def message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        if not self.collect_messages:
            return

        if self._result_data is not None and isinstance(self._result_data, ResultDataWithChildren):
            self._result_data.items.append(
                MessageData(
                    id=f"message-{len(self._result_data.items)}",
                    message=message,
                    level=level,
                    html=is_true(html),
                    timestamp=timestamp.strftime("%H:%M:%S") if isinstance(timestamp, datetime) else str(timestamp),
                )
            )

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if data.type in ["IF/ELSE ROOT", "TRY/EXCEPT ROOT"]:
            return
        if self._result_data is not None:
            kw_data = KeywordResultData(
                id=result.id,
                name=result.name if getattr(result, "name", None) else "",
                owner=result.owner if getattr(result, "owner", None) else "",
                source_name=result.source_name if getattr(result, "source_name", None) else "",
                doc=html_format(result.doc) if getattr(result, "doc", None) else "",
                args=list(result.args) if getattr(result, "args", None) else [],
                assign=list(result.assign) if getattr(result, "assign", None) else [],
                tags=list(result.tags) if getattr(result, "tags", None) else [],
                timeout=result.timeout if getattr(result, "timeout", None) else None,
                type=result.type,
                status=result.status,
                message=result.message,
                start_time=result.starttime,
                end_time=result.endtime,
                elapsed_time=(
                    make_elapsed_time_str(result.elapsedtime)
                    if get_robot_version() < (7, 0)
                    else make_elapsed_time_str(result.elapsed_time)
                ),
            )
            if self._result_data is not None and isinstance(self._result_data, ResultDataWithChildren):
                self._result_data.items.append(kw_data)
            self._result_data_stack.append(self._result_data)
            self._result_data = kw_data

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if data.type in ["IF/ELSE ROOT", "TRY/EXCEPT ROOT"]:
            return

        if self._result_data is not None:
            if isinstance(self._result_data, KeywordResultData):
                self._result_data.end_time = result.endtime
                self._result_data.elapsed_time = (
                    make_elapsed_time_str(result.elapsedtime)
                    if get_robot_version() < (7, 0)
                    else make_elapsed_time_str(result.elapsed_time)
                )
                self._result_data.status = result.status
                self._result_data.message = result.message

            self._result_data = self._result_data_stack.pop()

        if result.status == "FAIL":
            self._success = False
        elif result.status == "PASS" and self.last_result is not False:
            self._success = True

    def run_input(self) -> None:
        self.has_input.wait()
        if self._has_shutdown:
            self.executed.set()
            raise EOFError

        try:
            return super().run_input()
        finally:
            self.has_input.clear()
            self.executed.set()
