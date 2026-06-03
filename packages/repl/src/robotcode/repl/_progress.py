"""Run-progress event channel — a subscribable view of execution lifecycle.

`RunProgressEmitter` is an execution observer (register via
`BaseInterpreter.register_observer`) that re-broadcasts suite/test/keyword
start+end on independent `robotcode.core.event` channels. A consumer subscribes
only to what it needs — e.g. ``emitter.test_started.add(on_test)`` — and the
weakref-based listeners auto-clean on GC.

The console front-end does NOT use this: Robot's own console already shows
progress. It exists as the shared seam for future notebook / DAP front-ends.
Each event carries the running-model `data` and result-model `result` node —
the same pair Robot's logger delivers — so a subscriber decodes
name/status/source itself (no normalised payload is invented before a consumer
needs one).
"""

from typing import TYPE_CHECKING

from robotcode.core.event import event

if TYPE_CHECKING:
    from robot import result, running


class RunProgressEmitter:
    """Fans Robot's execution lifecycle out to per-event subscribable channels."""

    @event
    def suite_started(sender, data: "running.TestSuite", result: "result.TestSuite") -> None: ...

    @event
    def suite_ended(sender, data: "running.TestSuite", result: "result.TestSuite") -> None: ...

    @event
    def test_started(sender, data: "running.TestCase", result: "result.TestCase") -> None: ...

    @event
    def test_ended(sender, data: "running.TestCase", result: "result.TestCase") -> None: ...

    @event
    def keyword_started(sender, data: "running.Keyword", result: "result.Keyword") -> None: ...

    @event
    def keyword_ended(sender, data: "running.Keyword", result: "result.Keyword") -> None: ...

    # --- ExecutionObserver hooks → fire the matching channel ----------------

    def start_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
        self.suite_started(self, data, result)

    def end_suite(self, data: "running.TestSuite", result: "result.TestSuite") -> None:
        self.suite_ended(self, data, result)

    def start_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
        self.test_started(self, data, result)

    def end_test(self, data: "running.TestCase", result: "result.TestCase") -> None:
        self.test_ended(self, data, result)

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        self.keyword_started(self, data, result)

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        self.keyword_ended(self, data, result)
