from abc import ABC
import asyncio
from inspect import ismethod, isawaitable
from types import MethodType
from typing import Any, AsyncGenerator, Optional, Callable, Coroutine, Generic, List, MutableSet, TypeVar, Union, cast
import weakref
import threading

__all__ = ["AsyncEventGenerator", "AsyncEvent", "AsyncEventTaskGenerator", "AsyncEventTask"]

TResult = TypeVar("TResult")
TSender = TypeVar("TSender")
TParam = TypeVar("TParam")


class AsyncEventGeneratorBase(Generic[TSender, TParam, TResult], ABC):
    def __init__(self) -> None:
        self.lock = threading.Lock()

        self.methods_listeners: MutableSet[weakref.ref[Any]] = set()

    def add(self, callback: Callable[[TSender, TParam], TResult]) -> None:
        def remove_listener(ref: Any) -> None:
            with self.lock:
                self.methods_listeners.remove(ref)

        with self.lock:
            if ismethod(callback):
                self.methods_listeners.add(weakref.WeakMethod(cast(MethodType, callback), remove_listener))
            else:
                self.methods_listeners.add(weakref.ref(callback, remove_listener))

    def remove(self, callback: Callable[[TSender, TParam], TResult]) -> None:
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
                if isawaitable(result):
                    result = await result

                yield result


class AsyncEventGenerator(AsyncEventGeneratorBase[TSender, TParam, TResult]):
    def __call__(self, *args: Any, **kwargs: Any) -> "AsyncGenerator[TResult, None]":
        return self._notify(*args, **kwargs)


class AsyncEventWithResultList(AsyncEventGeneratorBase[TSender, TParam, TResult]):
    async def __call__(self, *args: Any, **kwargs: Any) -> List[TResult]:
        return [a async for a in self._notify(*args, **kwargs)]


class AsyncEvent(AsyncEventWithResultList[TSender, TParam, Any]):
    pass


class AsyncEventTaskGeneratorBase(
    AsyncEventGeneratorBase[TSender, TParam, Union[asyncio.Future[TResult], Coroutine[None, None, TResult]]]
):
    async def _notify(  # type: ignore
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> AsyncGenerator[TResult, None]:
        def _done(f: asyncio.Future[TResult]) -> None:
            if result_callback is not None and not f.cancelled():
                result_callback(f.result(), f.exception())

        awaitables: List[asyncio.Future[TResult]] = []
        for method_listener in self.methods_listeners:
            method = method_listener()
            if method is not None:
                future = asyncio.ensure_future(method(sender, param))
                if result_callback is not None:
                    future.add_done_callback(_done)
                awaitables.append(future)

        for a in await asyncio.gather(*awaitables):
            yield a


class AsyncEventTaskGenerator(AsyncEventTaskGeneratorBase[TSender, TParam, TResult]):
    def __call__(
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> "AsyncGenerator[TResult, None]":
        return self._notify(sender, param, result_callback=result_callback)


class AsyncEventTask(AsyncEventTaskGeneratorBase[TSender, TParam, TResult]):
    async def __call__(
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> List[TResult]:
        return [e async for e in self._notify(sender, param, result_callback=result_callback)]
