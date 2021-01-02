from abc import ABC
import asyncio
from inspect import ismethod
from types import MethodType
from typing import Any, AsyncGenerator, Callable, Generic, List, MutableSet, TypeVar, Union, cast
import weakref
import threading

__all__ = ["TCallback", "AsyncEventGenerator", "AsyncEvent"]

TResult = TypeVar("TResult")
TCallback = TypeVar("TCallback", bound=Union[Callable[..., Any]])


class AsyncEventGeneratorBase(Generic[TCallback, TResult], ABC):
    def __init__(self) -> None:
        self.lock = threading.Lock()

        self.methods_listeners: MutableSet[weakref.ref[Any]] = set()

    def add(self, callback: TCallback) -> None:
        def remove_listener(ref: Any) -> None:
            with self.lock:
                self.methods_listeners.remove(ref)

        with self.lock:
            if ismethod(callback):
                self.methods_listeners.add(weakref.WeakMethod(cast(MethodType, callback), remove_listener))
            else:
                self.methods_listeners.add(weakref.ref(callback, remove_listener))

    def remove(self, callback: TCallback) -> None:
        with self.lock:
            if ismethod(callback):
                self.methods_listeners.remove(weakref.WeakMethod(cast(MethodType, callback)))
            else:
                self.methods_listeners.remove(weakref.ref(callback))

    async def _notify(self, *args: Any, **kwargs: Any) -> AsyncGenerator[TResult, None]:
        for method_listener in self.methods_listeners:
            method = method_listener()
            if method is not None:
                result = method(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result

                yield result


class AsyncEventGenerator(AsyncEventGeneratorBase[TCallback, TResult]):
    def __call__(self, *args: Any, **kwargs: Any) -> "AsyncGenerator[TResult, None]":
        return self._notify(*args, **kwargs)


class AsyncEventWithResultList(AsyncEventGeneratorBase[TCallback, TResult]):
    async def __call__(self, *args: Any, **kwargs: Any) -> List[TResult]:
        return [a async for a in self._notify(*args, **kwargs)]


class AsyncEvent(AsyncEventWithResultList[TCallback, Any]):
    pass
