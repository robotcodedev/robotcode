from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Iterator, List, Optional, Protocol, Union, runtime_checkable
from uuid import uuid4

from robot.running import Keyword

from robotcode.core.utils.dataclasses import as_json
from robotcode.repl.base_interpreter import BaseInterpreter, is_true

from .html_writer import Element, create_keyword_html, create_message_html

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
    elapsed_time: Optional[float]

    items: List[ResultData] = field(default_factory=list)

    node_type: str = "keyword"


class Interpreter(BaseInterpreter):
    def __init__(
        self,
        files: Optional[List[Path]] = None,
    ) -> None:
        super().__init__()
        self.files = files
        self.has_input = Event()
        self.executed = Event()
        self._code: List[str] = []
        self._html_result: Optional[Element] = None
        self._result_stack: List[Element] = []
        self._output_stack: List[Element] = []
        self._shadow_marker: Optional[str] = None
        self._success: Optional[bool] = None
        self._result_data: Optional[ResultData] = None
        self._result_data_stack: List[ResultData] = []
        self.collect_messages: bool = False
        self._has_shutdown = False

    def shutdown(self) -> None:
        self._code = []
        self._has_shutdown = True
        self.has_input.set()
        # self.executed.set()

    def execute(self, source: str) -> ExecutionResult:
        self._result_stack = []
        self._result_data_stack = []

        self._success = None
        try:
            self._shadow_marker = str(uuid4())

            html_result = Element("div", classes=["robot-results"])

            with html_result.tag(
                "div", attributes={"data-shadow-marker": self._shadow_marker}, styles={"display": "none"}
            ):
                pass

            outer_test: Optional[Element] = None
            with html_result.tag("div", classes=["result_body"]) as body:
                with body.tag("div", classes=["test"]) as test:
                    with test.tag("div", classes=["children"], styles={"display": "block"}):
                        pass
                    outer_test = test

            self._html_result = outer_test
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
                        ExecutionOutput(
                            "x-application/robotframework-repl-html", html_result.as_str(only_children=True)
                        ),
                    ]
                    if self._success is not None
                    else []
                ),
            )
        except BaseException as e:
            return ExecutionResult(False, [ExecutionOutput("application/vnd.code.notebook.stderr", str(e))])

    def get_input(self) -> Iterator[Optional[Keyword]]:
        while self._code:
            s = self._code.pop(0)
            test, errors = self.get_test_body_from_string(s)
            if errors:
                raise CellInputError(errors)

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

        if level in ("DEBUG", "TRACE"):
            return

        if self._html_result is None:
            return

        items = next(
            (
                i
                for i in self._html_result.children
                if isinstance(i, Element) and i.tag_name == "div" and i.classes is not None and "children" in i.classes
            ),
            None,
        )
        if items is None:
            items = Element("div", classes=["children"])
            self._html_result.add_element(items)

        id = f"message-{len(items.children)}"

        message_data = create_message_html(id, message, level, html, timestamp, shadow_root_id=self._shadow_marker)
        items.add_element(message_data)

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
                doc=result.doc if getattr(result, "doc", None) else "",
                args=list(result.args) if getattr(result, "args", None) else [],
                assign=list(result.assign) if getattr(result, "assign", None) else [],
                tags=list(result.tags) if getattr(result, "tags", None) else [],
                timeout=result.timeout if getattr(result, "timeout", None) else None,
                type=result.type,
                status=result.status,
                message=result.message,
                start_time=result.starttime,
                end_time=result.endtime,
                elapsed_time=result.elapsedtime,
            )
            if self._result_data is not None and isinstance(self._result_data, ResultDataWithChildren):
                self._result_data.items.append(kw_data)
            self._result_data_stack.append(self._result_data)
            self._result_data = kw_data

        if self._html_result is not None:
            self._result_stack.append(self._html_result)
            kw = self.create_keyword_html_element(result)

            children = next(
                (
                    i
                    for i in self._html_result.children
                    if isinstance(i, Element)
                    and i.tag_name == "div"
                    and i.classes is not None
                    and "children" in i.classes
                ),
                None,
            )

            if children is None:
                self._html_result.add_element(kw)
            else:
                children.add_element(kw)

            self._html_result = kw

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        if data.type in ["IF/ELSE ROOT", "TRY/EXCEPT ROOT"]:
            return
        if self._result_data is not None:
            if isinstance(self._result_data, KeywordResultData):
                self._result_data.end_time = result.endtime
                self._result_data.elapsed_time = result.elapsedtime
                self._result_data.status = result.status
                self._result_data.message = result.message

            self._result_data = self._result_data_stack.pop()

        if result.status == "FAIL":
            self._success = False
        elif result.status == "PASS" and self.last_result is not False:
            self._success = True

        if self._html_result is not None and isinstance(self._html_result, Element):
            kw = self.create_keyword_html_element(result)

            old_children = next(
                (
                    i
                    for i in self._html_result.children
                    if isinstance(i, Element)
                    and i.tag_name == "div"
                    and i.classes is not None
                    and "children" in i.classes
                ),
                None,
            )
            if old_children is not None:
                new_children = next(
                    (
                        i
                        for i in kw.children
                        if isinstance(i, Element)
                        and i.tag_name == "div"
                        and i.classes is not None
                        and "children" in i.classes
                    ),
                    None,
                )
                if new_children is None:
                    new_children = Element("div", classes=["children"])
                    self._html_result.add_element(new_children)

                for old_child in old_children.children:
                    if not (
                        isinstance(old_child, Element)
                        and old_child.tag_name == "table"
                        and old_child.classes is not None
                        and "metadata" in old_child.classes
                    ):
                        new_children.add_element(old_child)

            self._html_result.children = kw.children

        self._html_result = self._result_stack.pop()

    def create_keyword_html_element(self, result: "result.Keyword") -> Element:
        return create_keyword_html(
            id=result.id,
            name=result.name if getattr(result, "name", None) else None,
            owner=result.owner if getattr(result, "owner", None) else None,
            source_name=result.source_name if getattr(result, "source_name", None) else None,
            doc=result.doc if getattr(result, "doc", None) else None,
            args=result.args if getattr(result, "args", None) else (),
            assign=result.assign if getattr(result, "assign", None) else (),
            tags=result.tags if getattr(result, "tags", None) else (),
            timeout=result.timeout if getattr(result, "timeout", None) else None,
            type=result.type,
            status=result.status,
            message=result.message,
            start_time=result.starttime,
            end_time=result.endtime,
            elapsed_time=result.elapsedtime,
            shadow_root_id=self._shadow_marker,
        )

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
