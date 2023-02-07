from __future__ import annotations

import inspect
import threading
import weakref
from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    List,
    MutableSet,
    Optional,
    Type,
    TypeVar,
    cast,
)

__all__ = ["EventIterator", "Event"]

_TResult = TypeVar("_TResult")
_TCallable = TypeVar("_TCallable", bound=Callable[..., Any])


class EventResultIteratorBase(Generic[_TCallable, _TResult]):
    def __init__(self) -> None:
        self._lock = threading.RLock()

        self._listeners: MutableSet[weakref.ref[Any]] = set()

    def add(self, callback: _TCallable) -> None:
        def remove_listener(ref: Any) -> None:
            with self._lock:
                self._listeners.remove(ref)

        with self._lock:
            if inspect.ismethod(callback):
                self._listeners.add(weakref.WeakMethod(callback, remove_listener))
            else:
                self._listeners.add(weakref.ref(callback, remove_listener))

    def remove(self, callback: _TCallable) -> None:
        with self._lock:
            try:
                if inspect.ismethod(callback):
                    self._listeners.remove(weakref.WeakMethod(callback))
                else:
                    self._listeners.remove(weakref.ref(callback))
            except KeyError:
                pass

    def __contains__(self, obj: Any) -> bool:
        if inspect.ismethod(obj):
            return weakref.WeakMethod(obj) in self._listeners

        return weakref.ref(obj) in self._listeners

    def __len__(self) -> int:
        return len(self._listeners)

    def __bool__(self) -> bool:
        return len(self._listeners) > 0

    def __iter__(self) -> Iterator[_TCallable]:
        for r in self._listeners:
            c = r()
            if c is not None:
                yield c

    def _notify(self, *args: Any, **kwargs: Any) -> Iterator[_TResult]:
        for method in set(self):
            yield method(*args, **kwargs)


class EventIterator(EventResultIteratorBase[_TCallable, _TResult]):
    def __call__(self, *args: Any, **kwargs: Any) -> Iterator[_TResult]:
        return self._notify(*args, **kwargs)


class Event(EventResultIteratorBase[_TCallable, _TResult]):
    def __call__(self, *args: Any, **kwargs: Any) -> List[_TResult]:
        return list(self._notify(*args, **kwargs))


_TEvent = TypeVar("_TEvent")


class EventDescriptorBase(Generic[_TCallable, _TResult, _TEvent]):
    def __init__(
        self, _func: _TCallable, factory: Callable[..., _TEvent], *factory_args: Any, **factory_kwargs: Any
    ) -> None:
        self._func = _func
        self.__factory = factory
        self.__factory_args = factory_args
        self.__factory_kwargs = factory_kwargs
        self._owner: Optional[Any] = None
        self._owner_name: Optional[str] = None

    def __set_name__(self, owner: Any, name: str) -> None:
        self._owner = owner
        self._owner_name = name

    def __get__(self, obj: Any, objtype: Type[Any]) -> _TEvent:
        if obj is None:
            return self  # type: ignore

        name = f"__event_{self._func.__name__}__"
        if not hasattr(obj, name):
            setattr(obj, name, self.__factory(*self.__factory_args, **self.__factory_kwargs))

        return cast("_TEvent", getattr(obj, name))


class event_iterator(EventDescriptorBase[_TCallable, Any, EventIterator[_TCallable, Any]]):  # noqa: N801
    def __init__(self, _func: _TCallable) -> None:
        super().__init__(_func, EventIterator[_TCallable, Any])


class event(EventDescriptorBase[_TCallable, Any, Event[_TCallable, Any]]):  # noqa: N801
    def __init__(self, _func: _TCallable) -> None:
        super().__init__(_func, Event[_TCallable, Any])
