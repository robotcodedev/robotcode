"""Tests for the run-progress event channel (`RunProgressEmitter`).

Drives a real in-process suite through a version-aware forwarding logger into
the emitter (an execution observer), with subscribers recording each event.
`robotcode.core.event` holds listeners weakly, so the recorder is kept alive as
a local for the duration of the run.
"""

import io
from typing import Any, List, Tuple

from robot.api import TestSuite as _RobotSuite
from robot.api import get_model
from robot.output import LOGGER

from robotcode.repl._progress import RunProgressEmitter
from robotcode.robot.utils import RF_VERSION

_SOURCE = "/tmp/progress_suite.robot"

SUITE = """\
*** Test Cases ***
T1
    Log    a
T2
    Log    b
"""


def _name(result: Any) -> str:
    return getattr(result, "name", None) or getattr(result, "longname", None) or "?"


def _run(emitter: RunProgressEmitter) -> None:
    if RF_VERSION >= (7, 0):
        import robot.output.loggerapi

        class _Logger(robot.output.loggerapi.LoggerApi):
            def start_suite(self, data: Any, result: Any) -> None:
                emitter.start_suite(data, result)

            def end_suite(self, data: Any, result: Any) -> None:
                emitter.end_suite(data, result)

            def start_test(self, data: Any, result: Any) -> None:
                emitter.start_test(data, result)

            def end_test(self, data: Any, result: Any) -> None:
                emitter.end_test(data, result)

            def start_keyword(self, data: Any, result: Any) -> None:
                emitter.start_keyword(data, result)

            def end_keyword(self, data: Any, result: Any) -> None:
                emitter.end_keyword(data, result)

            def start_body_item(self, data: Any, result: Any) -> None:
                emitter.start_keyword(data, result)

            def end_body_item(self, data: Any, result: Any) -> None:
                emitter.end_keyword(data, result)

    else:
        # RF<7: suite/test hooks get a single combined model; keyword hooks an args object.
        class _Logger:  # type: ignore[no-redef]
            def start_suite(self, model: Any) -> None:
                emitter.start_suite(model, model)

            def end_suite(self, model: Any) -> None:
                emitter.end_suite(model, model)

            def start_test(self, model: Any) -> None:
                emitter.start_test(model, model)

            def end_test(self, model: Any) -> None:
                emitter.end_test(model, model)

            def start_keyword(self, args: Any) -> None:
                emitter.start_keyword(args.data, args.result)

            def end_keyword(self, args: Any) -> None:
                emitter.end_keyword(args.data, args.result)

    logger = _Logger()
    LOGGER.register_logger(logger)
    try:
        with io.StringIO(SUITE) as src:
            model = get_model(src)
        model.source = _SOURCE
        suite = _RobotSuite.from_model(model)
        suite.run(output=None, log=None, report=None, console="none", stdout=io.StringIO(), stderr=io.StringIO())
    finally:
        LOGGER.unregister_logger(logger)


class _Recorder:
    """Strong-ref holder for the weakly-held event subscribers."""

    def __init__(self) -> None:
        self.events: List[Tuple[str, str]] = []

    def subscribe(self, emitter: RunProgressEmitter) -> None:
        emitter.suite_started.add(self._on_suite_started)
        emitter.suite_ended.add(self._on_suite_ended)
        emitter.test_started.add(self._on_test_started)
        emitter.test_ended.add(self._on_test_ended)
        emitter.keyword_started.add(self._on_keyword_started)

    def _on_suite_started(self, sender: Any, data: Any, result: Any) -> None:
        self.events.append(("suite_started", _name(result)))

    def _on_suite_ended(self, sender: Any, data: Any, result: Any) -> None:
        self.events.append(("suite_ended", _name(result)))

    def _on_test_started(self, sender: Any, data: Any, result: Any) -> None:
        self.events.append(("test_started", _name(result)))

    def _on_test_ended(self, sender: Any, data: Any, result: Any) -> None:
        self.events.append(("test_ended", _name(result)))

    def _on_keyword_started(self, sender: Any, data: Any, result: Any) -> None:
        self.events.append(("keyword_started", _name(result)))


def test_emitter_broadcasts_lifecycle_events() -> None:
    emitter = RunProgressEmitter()
    recorder = _Recorder()  # kept alive for the whole run (listeners are weak)
    recorder.subscribe(emitter)
    _run(emitter)

    events = recorder.events
    kinds = [kind for kind, _name in events]
    assert kinds[0] == "suite_started"
    assert kinds[-1] == "suite_ended"
    assert ("test_started", "T1") in events
    assert ("test_ended", "T1") in events
    assert ("test_started", "T2") in events
    assert ("test_ended", "T2") in events
    # a keyword inside a test was broadcast too (RF<7 reports `BuiltIn.Log`,
    # RF7 the short `Log`).
    assert any(kind == "keyword_started" and name.endswith("Log") for kind, name in events)
    # T1 fully runs before T2 starts
    assert events.index(("test_ended", "T1")) < events.index(("test_started", "T2"))


def test_unsubscribe_stops_delivery() -> None:
    emitter = RunProgressEmitter()
    seen: List[str] = []

    def on_test_started(sender: Any, data: Any, result: Any) -> None:
        seen.append(_name(result))

    emitter.test_started.add(on_test_started)
    emitter.test_started.remove(on_test_started)
    _run(emitter)
    assert seen == []
