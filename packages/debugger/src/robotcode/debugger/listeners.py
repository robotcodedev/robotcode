import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union, cast

from robot import result, running
from robot.model import Message

from .dap_types import Event, Model
from .debugger import Debugger


@dataclass
class RobotExecutionEventBody(Model):
    type: str
    id: str
    attributes: Optional[Dict[str, Any]] = None
    failed_keywords: Optional[List[Dict[str, Any]]] = None


class ListenerV2:
    ROBOT_LISTENER_API_VERSION = "2"

    def __init__(self) -> None:
        self.failed_keywords: Optional[List[Dict[str, Any]]] = None
        self.last_fail_message: Optional[str] = None

    def start_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance().send_event(
            self,
            Event(
                event="robotStarted",
                body=RobotExecutionEventBody(
                    type="suite",
                    id=f"{attributes.get('source', '')};{attributes.get('longname', '')}",
                    attributes=dict(attributes),
                ),
            ),
        )

        Debugger.instance().start_output_group(name, attributes, "SUITE")

        Debugger.instance().start_suite(name, attributes)

    def end_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance().end_suite(name, attributes)

        Debugger.instance().end_output_group(name, attributes, "SUITE")

        Debugger.instance().send_event(
            self,
            Event(
                event="robotEnded",
                body=RobotExecutionEventBody(
                    type="suite",
                    attributes=dict(attributes),
                    id=f"{attributes.get('source', '')};{attributes.get('longname', '')}",
                    failed_keywords=self.failed_keywords,
                ),
            ),
        )

        self.failed_keywords = None

    def start_test(self, name: str, attributes: Dict[str, Any]) -> None:
        self.failed_keywords = None

        Debugger.instance().send_event(
            self,
            Event(
                event="robotStarted",
                body=RobotExecutionEventBody(
                    type="test",
                    id=f"{attributes.get('source', '')};{attributes.get('longname', '')};"
                    f"{attributes.get('lineno', 0)}",
                    attributes=dict(attributes),
                ),
            ),
        )

        Debugger.instance().start_output_group(name, attributes, "TEST")

        Debugger.instance().start_test(name, attributes)

    def end_test(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance().end_test(name, attributes)

        Debugger.instance().end_output_group(name, attributes, "TEST")

        Debugger.instance().send_event(
            self,
            Event(
                event="robotEnded",
                body=RobotExecutionEventBody(
                    type="test",
                    id=f"{attributes.get('source', '')};{attributes.get('longname', '')};"
                    f"{attributes.get('lineno', 0)}",
                    attributes=dict(attributes),
                    failed_keywords=self.failed_keywords,
                ),
            ),
        )

        self.failed_keywords = None

    def start_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        if attributes["type"] in ["KEYWORD", "SETUP", "TEARDOWN"]:
            Debugger.instance().start_output_group(
                f"{name}({', '.join(repr(v) for v in attributes.get('args', []))})",
                attributes,
                attributes.get("type", None),
            )

        Debugger.instance().start_keyword(name, attributes)

    def end_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance().end_keyword(name, attributes)

        if attributes["type"] in ["KEYWORD", "SETUP", "TEARDOWN"]:
            Debugger.instance().end_output_group(name, attributes, attributes.get("type", None))

            if attributes["status"] == "FAIL" and attributes.get("source", None):
                if self.failed_keywords is None:
                    self.failed_keywords = []

                self.failed_keywords.insert(0, {"message": self.last_fail_message, **attributes})

    RE_FILE_LINE_MATCHER = re.compile(r".+\sin\sfile\s'(?P<file>.*)'\son\sline\s(?P<line>\d+):(?P<message>.*)")

    def log_message(self, message: Dict[str, Any]) -> None:
        if message["level"] in ["FAIL", "ERROR", "WARN"]:
            current_frame = Debugger.instance().full_stack_frames[0] if Debugger.instance().full_stack_frames else None

            if message["level"] == "FAIL":
                self.last_fail_message = message["message"]
                Debugger.instance().last_fail_message = self.last_fail_message

            source = current_frame.source if current_frame else None
            line = current_frame.line if current_frame else None
            column = current_frame.column if current_frame else None

            item_id = next(
                (
                    (
                        f"{Path(item.source).resolve() if item.source is not None else ''};{item.longname}"
                        if item.type == "SUITE"
                        else f"{Path(item.source).resolve() if item.source is not None else ''};"
                        f"{item.longname};{item.line}"
                    )
                    for item in Debugger.instance().full_stack_frames
                    if item.type in ["SUITE", "TEST"]
                ),
                None,
            )

            msg = None
            match = self.RE_FILE_LINE_MATCHER.match(message["message"])
            if match:
                source = match.group("file")
                line = int(match.group("line"))
                msg = match.group("message")
                column = 0

            Debugger.instance().send_event(
                self,
                Event(
                    event="robotLog",
                    body={
                        "itemId": item_id,
                        "source": source,
                        "lineno": line,
                        "column": column,
                        **dict(message),
                        **({"message": msg} if msg else {}),
                    },
                ),
            )

        Debugger.instance().log_message(message)

    def message(self, message: Dict[str, Any]) -> None:
        if message["level"] in ["FAIL", "ERROR", "WARN"]:
            current_frame = Debugger.instance().full_stack_frames[0] if Debugger.instance().full_stack_frames else None

            source = current_frame.source if current_frame else None
            line = current_frame.line if current_frame else None
            column = current_frame.column if current_frame else None

            item_id = next(
                (
                    (
                        f"{Path(item.source).resolve() if item.source is not None else ''};{item.longname}"
                        if item.type == "SUITE"
                        else f"{Path(item.source).resolve() if item.source is not None else ''};"
                        f"{item.longname};{item.line}"
                    )
                    for item in Debugger.instance().full_stack_frames
                    if item.type in ["SUITE", "TEST"]
                ),
                None,
            )

            msg = None
            match = self.RE_FILE_LINE_MATCHER.match(message["message"])
            if match:
                source = match.group("file")
                line = int(match.group("line"))
                msg = match.group("message")
                column = 0

            Debugger.instance().send_event(
                self,
                Event(
                    event="robotMessage",
                    body={
                        "itemId": item_id,
                        "source": source,
                        "lineno": line,
                        "column": column,
                        **dict(message),
                        **({"message": msg} if msg else {}),
                    },
                ),
            )

        Debugger.instance().message(message)

    def library_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def resource_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def variables_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def output_file(self, path: str) -> None:
        Debugger.instance().robot_output_file = path

    def log_file(self, path: str) -> None:
        Debugger.instance().robot_log_file = path

    def report_file(self, path: str) -> None:
        Debugger.instance().robot_report_file = path

    def xunit_file(self, path: str) -> None:
        pass

    def debug_file(self, path: str) -> None:
        pass

    def close(self) -> None:
        pass


class ListenerV3:
    ROBOT_LISTENER_API_VERSION = "3"

    def __init__(self) -> None:
        self._event_sended = False

    def start_suite(self, data: running.TestSuite, result: result.TestSuite) -> None:
        """Called when a suite starts."""

        def enqueue(item: Union[running.TestSuite, running.TestCase]) -> Iterator[str]:
            if isinstance(item, running.TestSuite):
                yield f"{Path(item.source).resolve() if item.source is not None else ''};{item.longname}"

                for s in item.suites:
                    yield from enqueue(s)
                for s in item.tests:
                    yield from enqueue(s)
                return

            yield f"{Path(item.source).resolve() if item.source is not None else ''};{item.longname};{item.lineno}"

        if self._event_sended:
            return

        items = list(reversed(list(enqueue(cast(running.TestSuite, data)))))

        Debugger.instance().send_event(
            self,
            Event(
                event="robotEnqueued",
                body={"items": items},
            ),
        )

        self._event_sended = True

    def end_suite(self, suite_data: running.TestSuite, suite_result: result.TestSuite) -> None:
        def report_status(
            data_item: Union[running.TestSuite, running.TestCase, None],
            result_item: Union[result.TestSuite, result.TestCase],
            message: str,
        ) -> None:
            if isinstance(result_item, result.TestCase):
                Debugger.instance().send_event(
                    self,
                    Event(
                        event="robotSetFailed",
                        body=RobotExecutionEventBody(
                            type="test",
                            attributes={
                                "longname": result_item.longname,
                                "status": str(result_item.status),
                                "elapsedtime": result_item.elapsedtime,
                                "source": str(result_item.source),
                                "lineno": data_item.lineno if data_item is not None else 0,
                                "message": result_item.message,
                            },
                            id=f"{result_item.source or ''};{result_item.longname or ''}"
                            + (
                                f";{data_item.lineno if data_item is not None else 0}"
                                if isinstance(result_item, result.TestCase)
                                else ""
                            ),
                        ),
                    ),
                )
            if isinstance(result_item, result.TestSuite):
                for r in result_item.suites:
                    p = next((i for i in data_item.suites if i.id == r.id), None) if data_item else None
                    report_status(p, r, message)
                for r in result_item.tests:
                    p = next((i for i in data_item.tests if i.id == r.id), None) if data_item else None
                    report_status(p, r, message)

        if suite_data.teardown and suite_result.teardown.status in ["FAIL", "SKIP"]:
            report_status(suite_data, suite_result, message=suite_result.message)

    def start_test(self, data: running.TestCase, result: result.TestCase) -> None:
        pass

    def end_test(self, data: running.TestCase, result: result.TestCase) -> None:
        pass

    def log_message(self, message: Message) -> None:
        pass

    def message(self, message: Message) -> None:
        pass
