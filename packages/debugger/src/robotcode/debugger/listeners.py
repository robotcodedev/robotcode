import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Union, cast

from robot import result, running
from robot.model import Message

from robotcode.core.utils.path import normalized_path

from .dap_types import Event, Model
from .debugger import Debugger, LogMessage
from .mixins import SyncedEventBody


@dataclass
class RobotFailure(Model):
    # indices into failed_keywords: the failed keyword whose message and caught mark are the failure's, and the failed
    # keywords from the innermost call out to the test
    keyword: int
    calls: List[int]


@dataclass
class RobotExecutionEventBody(Model, SyncedEventBody):
    type: str
    id: str
    name: str
    parent_id: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    failed_keywords: Optional[List[Dict[str, Any]]] = None
    # in the order their keywords ended
    failures: Optional[List[RobotFailure]] = None
    source: Optional[str] = None
    lineno: Optional[int] = None
    synced: bool = True


@dataclass
class RobotEnqueuedEventBody(Model, SyncedEventBody):
    items: List[str]
    synced: bool = True


@dataclass
class RobotLogMessageEventBody(Model, SyncedEventBody):
    item_id: Optional[str]

    message: Optional[str]
    level: Optional[str]
    timestamp: Optional[str]
    html: Optional[str]

    source: Optional[str] = None
    lineno: Optional[int] = None
    column: Optional[int] = None

    synced: bool = True


def source_from_attributes(attributes: Dict[str, Any]) -> str:
    s = attributes.get("source", "")
    if s:
        return str(normalized_path(Path(s)))

    return s or ""


class ListenerV2:
    ROBOT_LISTENER_API_VERSION = "2"

    def __init__(self) -> None:
        self.failed_keywords: Optional[List[Dict[str, Any]]] = None
        # the number of failed keywords when each running keyword or control structure started; per depth, the failed
        # keywords of the last TRY branch there, and those of them that its EXCEPT branch caught
        self.failed_keyword_marks: List[int] = []
        # by the id of a failed keyword, the nearest failed keyword it ran in
        self.failed_keyword_parents: Dict[int, Dict[str, Any]] = {}
        # per running keyword or control structure, whether it logged a failure itself, as Robot Framework does for the
        # keyword whose error it is; and the ids of the failed keywords that did
        self.failure_logged: List[bool] = []
        self.failed_keywords_with_own_failure: Set[int] = set()
        self.try_failures: Dict[int, List[Dict[str, Any]]] = {}
        self.caught_by_except: Dict[int, List[Dict[str, Any]]] = {}
        self.last_fail_message: Optional[str] = None
        self.suite_id_stack: List[str] = []

    def start_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        id = f"{source_from_attributes(attributes)};{attributes.get('longname', '')}"

        Debugger.instance.send_event(
            self,
            Event(
                event="robotStarted",
                body=RobotExecutionEventBody(
                    type="suite",
                    name=name,
                    id=id,
                    parent_id=self.suite_id_stack[-1] if self.suite_id_stack else None,
                    attributes=dict(attributes),
                    source=source_from_attributes(attributes) or None,
                    lineno=attributes.get("lineno", None),
                ),
            ),
        )

        Debugger.instance.start_output_group(name, attributes, "SUITE")

        Debugger.instance.start_suite(name, attributes)
        self.suite_id_stack.append(id)

    def end_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        id = f"{source_from_attributes(attributes)};{attributes.get('longname', '')}"
        Debugger.instance.end_suite(name, attributes)

        Debugger.instance.end_output_group(name, attributes, "SUITE")

        Debugger.instance.send_event(
            self,
            Event(
                event="robotEnded",
                body=RobotExecutionEventBody(
                    type="suite",
                    name=name,
                    attributes=dict(attributes),
                    id=id,
                    parent_id=self.suite_id_stack[-1] if self.suite_id_stack else None,
                    failed_keywords=self.failed_keywords,
                    failures=self._failures(),
                    source=source_from_attributes(attributes) or None,
                    lineno=attributes.get("lineno", None),
                ),
            ),
        )
        self.suite_id_stack.pop()
        self._forget_failed_keywords()

    def start_test(self, name: str, attributes: Dict[str, Any]) -> None:
        self._forget_failed_keywords()

        Debugger.instance.send_event(
            self,
            Event(
                event="robotStarted",
                body=RobotExecutionEventBody(
                    type="test",
                    name=name,
                    id=f"{source_from_attributes(attributes)};{attributes.get('longname', '')};"
                    f"{attributes.get('lineno', 0)}",
                    parent_id=self.suite_id_stack[-1] if self.suite_id_stack else None,
                    attributes=dict(attributes),
                    source=source_from_attributes(attributes) or None,
                    lineno=attributes.get("lineno", None),
                ),
            ),
        )

        Debugger.instance.start_output_group(name, attributes, "TEST")

        Debugger.instance.start_test(name, attributes)

    def end_test(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance.end_test(name, attributes)

        Debugger.instance.end_output_group(name, attributes, "TEST")

        Debugger.instance.send_event(
            self,
            Event(
                event="robotEnded",
                body=RobotExecutionEventBody(
                    type="test",
                    name=name,
                    id=f"{source_from_attributes(attributes)};{attributes.get('longname', '')};"
                    f"{attributes.get('lineno', 0)}",
                    parent_id=self.suite_id_stack[-1] if self.suite_id_stack else None,
                    attributes=dict(attributes),
                    failed_keywords=self.failed_keywords,
                    failures=self._failures(),
                    source=source_from_attributes(attributes) or None,
                    lineno=attributes.get("lineno", None),
                ),
            ),
        )

        self._forget_failed_keywords()

    def _forget_failed_keywords(self) -> None:
        self.failed_keywords = None
        self.failed_keyword_parents = {}
        self.failed_keywords_with_own_failure = set()

    def _failures(self) -> Optional[List[RobotFailure]]:
        keywords = self.failed_keywords
        if not keywords:
            return None

        index = {id(keyword): i for i, keyword in enumerate(keywords)}
        parents = self.failed_keyword_parents

        # the failed keywords inside a keyword are those it is the parent of that are caught, or not caught, like it; a
        # caught one inside a keyword that is not caught was caught within it and stays a failure of its own
        def is_inside(keyword: Dict[str, Any], parent: Optional[Dict[str, Any]]) -> bool:
            return parent is not None and bool(parent.get("caught")) == bool(keyword.get("caught"))

        inside: Dict[int, List[Dict[str, Any]]] = {}
        for keyword in keywords:
            parent = parents.get(id(keyword))
            if parent is not None and is_inside(keyword, parent):
                inside.setdefault(id(parent), []).append(keyword)

        # a keyword that logged a failure of its own after failures inside it turned theirs into its own, as Wait Until
        # Keyword Succeeds does after its last attempt; one that passes them on or collects them logs none
        def turns_into_own(keyword: Dict[str, Any]) -> bool:
            return bool(inside.get(id(keyword))) and id(keyword) in self.failed_keywords_with_own_failure

        def within(keyword: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
            current, parent = keyword, parents.get(id(keyword))
            while parent is not None and is_inside(current, parent):
                yield parent
                current, parent = parent, parents.get(id(parent))

        def outwards(keyword: Dict[str, Any]) -> List[int]:
            calls = []
            current: Optional[Dict[str, Any]] = keyword
            while current is not None:
                calls.append(index[id(current)])
                current = parents.get(id(current))
            return calls

        # the calls of the newest failure inside the keyword, up to it
        def last_inside(keyword: Dict[str, Any]) -> List[int]:
            for candidate in keywords:
                if inside.get(id(candidate)):
                    continue
                calls = [index[id(candidate)]]
                for outer in within(candidate):
                    if outer is keyword:
                        return calls
                    calls.append(index[id(outer)])
            return []

        failures = []
        for keyword in reversed(keywords):
            if any(turns_into_own(outer) for outer in within(keyword)):
                continue
            if turns_into_own(keyword):
                failures.append(RobotFailure(index[id(keyword)], last_inside(keyword) + outwards(keyword)))
            elif not inside.get(id(keyword)):
                failures.append(RobotFailure(index[id(keyword)], outwards(keyword)))

        return failures

    def start_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        self.failed_keyword_marks.append(len(self.failed_keywords or []))
        self.failure_logged.append(False)

        if attributes["type"] in ["KEYWORD", "SETUP", "TEARDOWN"]:
            Debugger.instance.start_output_group(
                f"{name}({', '.join(repr(v) for v in attributes.get('args', []))})",
                attributes,
                attributes.get("type"),
            )

        # if Debugger.instance.state != State.CallKeyword:
        #     Debugger.instance.send_event(
        #         self,
        #         Event(
        #             event="robotStarted",
        #             body=RobotExecutionEventBody(
        #                 type="keyword",
        #                 name=name,
        #                 id=f"{source_from_attributes(attributes)};{name};{attributes.get('lineno', 0)}",
        #                 parent_id=self.suite_id_stack[-1] if self.suite_id_stack else None,
        #                 attributes=dict(attributes),
        #                 source=source_from_attributes(attributes) or None,
        #                 lineno=attributes.get("lineno", None),
        #             ),
        #         ),
        #     )

        Debugger.instance.start_keyword(name, attributes)

    def end_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance.end_keyword(name, attributes)
        mark = self.failed_keyword_marks.pop() if self.failed_keyword_marks else 0
        failure_logged = self.failure_logged.pop() if self.failure_logged else False

        # if Debugger.instance.state != State.CallKeyword:
        #     Debugger.instance.send_event(
        #         self,
        #         Event(
        #             event="robotEnded",
        #             body=RobotExecutionEventBody(
        #                 type="keyword",
        #                 name=name,
        #                 id=f"{source_from_attributes(attributes)};{name};{attributes.get('lineno', 0)}",
        #                 parent_id=self.suite_id_stack[-1] if self.suite_id_stack else None,
        #                 attributes=dict(attributes),
        #                 source=source_from_attributes(attributes) or None,
        #                 lineno=attributes.get("lineno", None),
        #             ),
        #         ),
        #     )

        if attributes["type"] in ["KEYWORD", "SETUP", "TEARDOWN"]:
            Debugger.instance.end_output_group(name, attributes, attributes.get("type"))

            if attributes["status"] == "FAIL" and attributes.get("source"):
                if self.failed_keywords is None:
                    self.failed_keywords = []

                keyword = {"message": self.last_fail_message, **attributes}
                # it is the nearest failed keyword around those that ended since it started and have none yet
                for inner in self.failed_keywords[: max(0, len(self.failed_keywords) - mark)]:
                    self.failed_keyword_parents.setdefault(id(inner), keyword)
                self.failed_keywords.insert(0, keyword)
                if failure_logged:
                    self.failed_keywords_with_own_failure.add(id(keyword))

        self._mark_caught_failures(attributes, mark, len(self.failed_keyword_marks))

    def _mark_caught_failures(self, attributes: Dict[str, Any], mark: int, depth: int) -> None:
        # Robot Framework's log expands a failed test only along what failed, so a failure inside a keyword or control
        # structure that did not fail was caught, as by Run Keyword And Ignore Error. Listener version 2 gets the
        # branches of a TRY/EXCEPT but not the TRY/EXCEPT, whose status the log follows: an EXCEPT branch that passed
        # caught the failures of its TRY branch, unless the FINALLY branch fails and with it the TRY/EXCEPT
        kind, status = attributes["type"], attributes["status"]
        failed = self.failed_keywords or []
        inside = failed[: max(0, len(failed) - mark)]
        if status != "FAIL":
            for keyword in inside:
                keyword["caught"] = True
        if kind == "TRY":
            self.try_failures[depth] = inside
            self.caught_by_except[depth] = []
        elif kind == "EXCEPT" and status == "PASS":
            caught = [keyword for keyword in self.try_failures.get(depth, []) if not keyword.get("caught")]
            for keyword in caught:
                keyword["caught"] = True
            self.caught_by_except[depth] = caught
        elif kind == "FINALLY" and status == "FAIL":
            for keyword in self.caught_by_except.pop(depth, []):
                keyword.pop("caught", None)

    RE_FILE_LINE_MATCHER = re.compile(r".+\sin\sfile\s'(?P<file>.*)'\son\sline\s(?P<line>\d+):(?P<message>.*)")

    def log_message(self, message: LogMessage) -> None:
        if message["level"] in ["FAIL", "ERROR", "WARN"]:
            current_frame = Debugger.instance.full_stack_frames[0] if Debugger.instance.full_stack_frames else None

            if message["level"] == "FAIL":
                self.last_fail_message = message["message"]
                Debugger.instance.last_fail_message = self.last_fail_message
                if self.failure_logged:
                    self.failure_logged[-1] = True

            source = current_frame.source if current_frame else None
            line = current_frame.line if current_frame else None
            column = current_frame.column if current_frame else None

            item_id = next(
                (
                    (
                        f"{normalized_path(Path(item.source)) if item.source is not None else ''};{item.longname}"
                        if item.type == "SUITE"
                        else f"{normalized_path(Path(item.source)) if item.source is not None else ''};"
                        f"{item.longname};{item.line}"
                    )
                    for item in Debugger.instance.full_stack_frames
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

            Debugger.instance.send_event(
                self,
                Event(
                    event="robotLog",
                    body=RobotLogMessageEventBody(
                        item_id=item_id,
                        message=msg if msg else message.get("message", None),
                        level=message.get("level", None),
                        timestamp=message.get("timestamp", None),
                        html=message.get("html", None),
                        source=source,
                        lineno=line,
                        column=column,
                    ),
                ),
            )

        Debugger.instance.log_message(message)

    def message(self, message: LogMessage) -> None:
        if message["level"] in ["FAIL", "ERROR", "WARN"]:
            current_frame = Debugger.instance.full_stack_frames[0] if Debugger.instance.full_stack_frames else None

            source = current_frame.source if current_frame else None
            line = current_frame.line if current_frame else None
            column = current_frame.column if current_frame else None

            item_id = next(
                (
                    (
                        f"{normalized_path(Path(item.source)) if item.source is not None else ''};{item.longname}"
                        if item.type == "SUITE"
                        else f"{normalized_path(Path(item.source)) if item.source is not None else ''};"
                        f"{item.longname};{item.line}"
                    )
                    for item in Debugger.instance.full_stack_frames
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

            Debugger.instance.send_event(
                self,
                Event(
                    event="robotMessage",
                    body=RobotLogMessageEventBody(
                        item_id=item_id,
                        message=msg if msg else message.get("message", None),
                        level=message.get("level", None),
                        timestamp=message.get("timestamp", None),
                        html=message.get("html", None),
                        source=source,
                        lineno=line,
                        column=column,
                    ),
                ),
            )

        Debugger.instance.message(message)

    def library_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def resource_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def variables_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def output_file(self, path: str) -> None:
        Debugger.instance.robot_output_file = path

    def log_file(self, path: str) -> None:
        Debugger.instance.robot_log_file = path

    def report_file(self, path: str) -> None:
        Debugger.instance.robot_report_file = path

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

        def enqueue(
            item: Union[running.TestSuite, running.TestCase],
        ) -> Iterator[str]:
            if isinstance(item, running.TestSuite):
                yield f"{normalized_path(item.source) if item.source is not None else ''};{item.longname}"

                for s in item.suites:
                    yield from enqueue(s)
                for s in item.tests:
                    yield from enqueue(s)
                return

            yield (f"{normalized_path(item.source) if item.source is not None else ''};{item.longname};{item.lineno}")

        if self._event_sended:
            return

        items = list(reversed(list(enqueue(cast(running.model.TestSuite, data)))))

        Debugger.instance.send_event(self, Event(event="robotEnqueued", body=RobotEnqueuedEventBody(items)))

        self._event_sended = True

    def end_suite(self, suite_data: running.TestSuite, suite_result: result.TestSuite) -> None:
        def report_status(
            data_item: Union[running.TestSuite, running.TestCase, None],
            result_item: Union[result.TestSuite, result.TestCase],
            message: str,
        ) -> None:
            if isinstance(result_item, result.TestCase):
                Debugger.instance.send_event(
                    self,
                    Event(
                        event="robotSetFailed",
                        body=RobotExecutionEventBody(
                            type="test",
                            name=result_item.name,
                            attributes={
                                "longname": result_item.longname,
                                "status": str(result_item.status),
                                "elapsedtime": result_item.elapsedtime,
                                "source": str(result_item.source),
                                "lineno": data_item.lineno if data_item is not None else 0,
                                "message": result_item.message,
                            },
                            id=f"{normalized_path(Path(result_item.source)) if result_item.source else ''};"
                            f"{result_item.longname or ''}"
                            + (
                                f";{data_item.lineno if data_item is not None else 0}"
                                if isinstance(result_item, result.TestCase)
                                else ""
                            ),
                            source=str(normalized_path(Path(result_item.source))) if result_item.source else None,
                            lineno=data_item.lineno if data_item else None,
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

        if suite_data.teardown and suite_result.teardown.status in [
            "FAIL",
            "SKIP",
        ]:
            report_status(suite_data, suite_result, message=suite_result.message)

    def start_test(self, data: running.TestCase, result: result.TestCase) -> None:
        pass

    def end_test(self, data: running.TestCase, result: result.TestCase) -> None:
        pass

    def log_message(self, message: Message) -> None:
        pass

    def message(self, message: Message) -> None:
        pass
