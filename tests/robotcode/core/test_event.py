"""Events call their listeners and hold them only weakly.

A listener that dies leaves its event on its own. An event and the object it belongs to are freed
as soon as nothing refers to them anymore, without the garbage collector.
"""

import gc
import sys
import threading
import weakref
from typing import Any, Iterator, List, Optional, Tuple

import pytest

from robotcode.core.event import Event, EventIterator, event, event_iterator


class Source:
    @event
    def changed(sender, value: int) -> Optional[int]: ...

    @event_iterator
    def changing(sender, value: int) -> Optional[int]: ...


class Listener:
    def __init__(self, result: int = 0) -> None:
        self.calls: List[Tuple[Any, int]] = []
        self.result = result

    def on_changed(self, sender: Any, value: int) -> int:
        self.calls.append((sender, value))
        return self.result


@pytest.fixture
def without_gc() -> Iterator[None]:
    """While the test runs, only reference counting frees objects."""
    gc.collect()
    gc.disable()
    try:
        yield
    finally:
        gc.enable()


@pytest.fixture
def unraisable() -> Iterator[List[Any]]:
    """Exceptions in callbacks of weak references, which Python only reports."""
    reported: List[Any] = []
    hook = sys.unraisablehook
    sys.unraisablehook = reported.append
    try:
        yield reported
    finally:
        sys.unraisablehook = hook


def test_a_listener_is_called_with_the_sender_and_the_arguments() -> None:
    source, listener = Source(), Listener()
    source.changed.add(listener.on_changed)

    source.changed(source, 42)

    assert listener.calls == [(source, 42)]


def test_an_event_returns_the_results_of_its_listeners() -> None:
    source, first, second = Source(), Listener(1), Listener(2)
    source.changed.add(first.on_changed)
    source.changed.add(second.on_changed)

    assert set(source.changed(source, 0)) == {1, 2}


def test_an_event_iterator_calls_the_listeners_while_it_is_iterated() -> None:
    source, listener = Source(), Listener(3)
    source.changing.add(listener.on_changed)

    results = source.changing(source, 1)
    assert listener.calls == []

    assert list(results) == [3]
    assert listener.calls == [(source, 1)]


def test_a_failing_listener_gives_its_exception_as_result() -> None:
    source = Source()

    def failing(sender: Any, value: int) -> int:
        raise ValueError("failed")

    source.changed.add(failing)

    results = source.changed(source, 0)

    assert len(results) == 1
    assert isinstance(results[0], ValueError)


def test_the_callback_filter_selects_the_listeners() -> None:
    source, first, second = Source(), Listener(1), Listener(2)
    source.changed.add(first.on_changed)
    source.changed.add(second.on_changed)

    assert source.changed(source, 0, callback_filter=lambda c: c == first.on_changed) == [1]
    assert second.calls == []


def test_remove_drops_a_method_and_a_function() -> None:
    source, listener = Source(), Listener()

    def function_listener(sender: Any, value: int) -> int:
        return 0

    source.changed.add(listener.on_changed)
    source.changed.add(function_listener)

    source.changed.remove(listener.on_changed)
    source.changed.remove(function_listener)
    source.changed(source, 0)

    assert len(source.changed) == 0
    assert listener.calls == []


def test_removing_a_listener_that_was_never_added_does_nothing() -> None:
    source, listener, other = Source(), Listener(), Listener()
    source.changed.add(listener.on_changed)

    source.changed.remove(other.on_changed)

    assert len(source.changed) == 1


def test_contains_len_and_bool_reflect_the_listeners() -> None:
    source, listener = Source(), Listener()
    assert not source.changed
    assert len(source.changed) == 0

    source.changed.add(listener.on_changed)

    assert source.changed
    assert len(source.changed) == 1
    assert listener.on_changed in source.changed
    assert Listener().on_changed not in source.changed


def test_a_listener_added_twice_is_called_once() -> None:
    source, listener = Source(), Listener()
    source.changed.add(listener.on_changed)
    source.changed.add(listener.on_changed)

    source.changed(source, 0)

    assert len(source.changed) == 1
    assert len(listener.calls) == 1


def test_every_object_has_its_own_events() -> None:
    first, second, listener = Source(), Source(), Listener()
    first.changed.add(listener.on_changed)

    second.changed(second, 0)

    assert listener.calls == []
    assert first.changed is first.changed
    assert first.changed is not second.changed
    assert isinstance(first.changed, Event)
    assert isinstance(first.changing, EventIterator)


def test_a_listener_that_dies_leaves_its_event(without_gc: None, unraisable: List[Any]) -> None:
    source, listener = Source(), Listener()

    def function_listener(sender: Any, value: int) -> int:
        return 0

    source.changed.add(listener.on_changed)
    source.changed.add(function_listener)
    source.changing.add(listener.on_changed)

    del listener, function_listener

    assert len(source.changed) == 0
    assert len(source.changing) == 0
    assert source.changed(source, 0) == []
    assert unraisable == []


def test_an_event_with_listeners_is_freed_with_its_object(without_gc: None) -> None:
    source, listener = Source(), Listener()
    source.changed.add(listener.on_changed)
    source.changing.add(listener.on_changed)
    references: List["weakref.ref[Any]"] = [
        weakref.ref(source),
        weakref.ref(source.changed),
        weakref.ref(source.changing),
    ]

    del source

    assert [r() for r in references] == [None, None, None]


def test_a_listener_that_dies_after_its_event_raises_nothing(without_gc: None, unraisable: List[Any]) -> None:
    source, listener = Source(), Listener()
    source.changed.add(listener.on_changed)
    # the weak reference to the listener outlives the event, so it still calls back when the listener dies
    listener_reference = next(iter(source.changed._listeners))

    del source
    del listener

    assert unraisable == []
    assert listener_reference() is None


def test_listeners_can_come_and_go_while_other_threads_call_the_event(unraisable: List[Any]) -> None:
    source = Source()
    errors: List[BaseException] = []
    stop = threading.Event()

    def call() -> None:
        while not stop.is_set():
            errors.extend(r for r in source.changed(source, 0) if isinstance(r, BaseException))

    def come_and_go() -> None:
        for i in range(500):
            listener = Listener()
            source.changed.add(listener.on_changed)
            if i % 2:
                source.changed.remove(listener.on_changed)
            # every other listener dies when the next one replaces it

    callers = [threading.Thread(target=call) for _ in range(2)]
    changers = [threading.Thread(target=come_and_go) for _ in range(4)]
    for thread in callers + changers:
        thread.start()
    for thread in changers:
        thread.join()
    stop.set()
    for thread in callers:
        thread.join()

    assert errors == []
    assert unraisable == []
    assert len(source.changed) == 0
