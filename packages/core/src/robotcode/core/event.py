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
    Union,
    cast,
)

from typing_extensions import ParamSpec

__all__ = ["event_iterator", "event"]

_TResult = TypeVar("_TResult")
_TParams = ParamSpec("_TParams")


class EventResultIteratorBase(Generic[_TParams, _TResult]):
    def __init__(self) -> None:
        self._lock = threading.RLock()

        self._listeners: MutableSet[weakref.ref[Any]] = set()

    def __remove_listener(self, ref: Any) -> None:
        with self._lock:
            self._listeners.remove(ref)

    def add(self, callback: Callable[_TParams, _TResult]) -> None:
        with self._lock:
            if inspect.ismethod(callback):
                self._listeners.add(weakref.WeakMethod(callback, self.__remove_listener))
            else:
                self._listeners.add(weakref.ref(callback, self.__remove_listener))

    def remove(self, callback: Callable[_TParams, _TResult]) -> None:
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

    def __iter__(self) -> Iterator[Callable[_TParams, _TResult]]:
        for r in list(self._listeners):
            c = r()
            if c is not None:
                yield c

    def _notify(
        self,
        *__args: _TParams.args,
        return_exceptions: Optional[bool] = True,
        callback_filter: Optional[Callable[[Callable[..., Any]], bool]] = None,
        **__kwargs: _TParams.kwargs,
    ) -> Iterator[Union[_TResult, BaseException]]:
        for method in filter(
            lambda x: callback_filter(x) if callback_filter is not None else True,
            set(self),
        ):
            try:
                yield method(*__args, **__kwargs)
            except BaseException as e:
                if return_exceptions:
                    yield e
                else:
                    raise


class EventIterator(EventResultIteratorBase[_TParams, _TResult]):
    def __call__(
        self,
        *__args: _TParams.args,
        callback_filter: Optional[Callable[[Callable[..., Any]], bool]] = None,
        **__kwargs: _TParams.kwargs,
    ) -> Iterator[Union[_TResult, BaseException]]:
        return self._notify(*__args, callback_filter=callback_filter, **__kwargs)


class Event(EventResultIteratorBase[_TParams, _TResult]):
    def __call__(
        self,
        *__args: _TParams.args,
        callback_filter: Optional[Callable[[Callable[..., Any]], bool]] = None,
        **__kwargs: _TParams.kwargs,
    ) -> List[Union[_TResult, BaseException]]:
        return list(self._notify(*__args, callback_filter=callback_filter, **__kwargs))


_TEvent = TypeVar("_TEvent")


class EventDescriptorBase(Generic[_TParams, _TResult, _TEvent]):
    def __init__(
        self,
        _func: Callable[_TParams, _TResult],
        factory: Callable[..., _TEvent],
        *factory_args: Any,
        **factory_kwargs: Any,
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
            setattr(
                obj,
                name,
                self.__factory(*self.__factory_args, **self.__factory_kwargs),
            )

        return cast("_TEvent", getattr(obj, name))


class event_iterator(EventDescriptorBase[_TParams, _TResult, EventIterator[_TParams, _TResult]]):  # noqa: N801
    def __init__(self, _func: Callable[_TParams, _TResult]) -> None:
        super().__init__(_func, EventIterator[_TParams, _TResult])


class event(EventDescriptorBase[_TParams, _TResult, Event[_TParams, _TResult]]):  # noqa: N801
    def __init__(self, _func: Callable[_TParams, _TResult]) -> None:
        super().__init__(_func, Event[_TParams, _TResult])
