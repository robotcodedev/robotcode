import asyncio
import threading
import weakref
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from inspect import isawaitable, ismethod
from types import MethodType
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Generic,
    List,
    MutableSet,
    Optional,
    TypeVar,
    Union,
    cast,
)

__all__ = [
    "AsyncEventGenerator",
    "AsyncEvent",
    "AsyncTaskEventGenerator",
    "AsyncTaskEvent",
    "AsyncThreadingEventGenerator",
    "AsyncThreadingEvent",
]

TResult = TypeVar("TResult")
TSender = TypeVar("TSender")
TParam = TypeVar("TParam")


class AsyncEventGeneratorBase(Generic[TSender, TParam, TResult], ABC):
    def __init__(self) -> None:
        self.lock = threading.Lock()

        self.listeners: MutableSet[weakref.ref[Any]] = set()

    def add(self, callback: Callable[[TSender, TParam], TResult]) -> None:
        def remove_listener(ref: Any) -> None:
            with self.lock:
                self.listeners.remove(ref)

        with self.lock:
            if ismethod(callback):
                self.listeners.add(weakref.WeakMethod(cast(MethodType, callback), remove_listener))
            else:
                self.listeners.add(weakref.ref(callback, remove_listener))

    def remove(self, callback: Callable[[TSender, TParam], TResult]) -> None:
        with self.lock:
            if ismethod(callback):
                self.listeners.remove(weakref.WeakMethod(cast(MethodType, callback)))
            else:
                self.listeners.remove(weakref.ref(callback))

    async def _notify(self, *args: Any, **kwargs: Any) -> AsyncIterator[TResult]:
        for method_listener in self.listeners:
            method = method_listener()
            if method is not None:
                result = method(*args, **kwargs)
                if isawaitable(result):
                    result = await result

                yield result


class AsyncEventGenerator(AsyncEventGeneratorBase[TSender, TParam, TResult]):
    def __call__(self, *args: Any, **kwargs: Any) -> AsyncIterator[TResult]:
        return self._notify(*args, **kwargs)


class AsyncEventWithResultList(AsyncEventGeneratorBase[TSender, TParam, TResult]):
    async def __call__(self, *args: Any, **kwargs: Any) -> List[TResult]:
        return [a async for a in self._notify(*args, **kwargs)]


class AsyncEvent(AsyncEventWithResultList[TSender, TParam, Any]):
    pass


class AsyncTaskEventGeneratorBase(
    AsyncEventGeneratorBase[TSender, TParam, Union[asyncio.Future[TResult], Awaitable[TResult]]]
):
    def __init__(self, *, ignore_exceptions: Optional[bool] = True) -> None:
        super().__init__()
        self.ignore_exceptions = ignore_exceptions

    async def _notify(  # type: ignore
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> AsyncIterator[TResult]:
        def _done(f: asyncio.Future[TResult]) -> None:
            if result_callback is not None:
                try:
                    result_callback(f.result(), f.exception())
                except KeyboardInterrupt:
                    raise
                except BaseException as e:
                    result_callback(None, e)

        awaitables: List[asyncio.Future[TResult]] = []
        for method_listener in self.listeners:
            method = method_listener()
            if method is not None:
                future = asyncio.ensure_future(method(sender, param))
                if result_callback is not None:
                    future.add_done_callback(_done)
                awaitables.append(future)

        for a in await asyncio.gather(*awaitables, return_exceptions=True):
            if isinstance(a, BaseException) and self.ignore_exceptions:
                continue
            yield cast("TResult", a)


class AsyncTaskEventGenerator(AsyncTaskEventGeneratorBase[TSender, TParam, TResult]):
    def __call__(
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> AsyncIterator[TResult]:
        return self._notify(sender, param, result_callback=result_callback)


class AsyncTaskEvent(AsyncTaskEventGeneratorBase[TSender, TParam, TResult]):
    async def __call__(
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> List[TResult]:
        return [e async for e in self._notify(sender, param, result_callback=result_callback)]


class AsyncThreadingEventGeneratorBase(
    AsyncEventGeneratorBase[TSender, TParam, Union[asyncio.Future[TResult], Awaitable[TResult]]]
):
    executor: ThreadPoolExecutor

    def __init__(
        self, executor: Optional[ThreadPoolExecutor] = None, *, ignore_exceptions: Optional[bool] = True
    ) -> None:
        super().__init__()

        if executor is None:
            self.executor = ThreadPoolExecutor()
            self._own_executor = True
        else:
            self.executor = executor
            self._own_executor = False

        self.ignore_exceptions = ignore_exceptions

    def __del__(self) -> None:
        if self._own_executor:
            self.executor.shutdown(False)

    @staticmethod
    def _run_in_asyncio_thread(
        executor: ThreadPoolExecutor, coro: Union[asyncio.Future[TResult], Awaitable[TResult]]
    ) -> asyncio.Future[TResult]:
        def run(loop: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            finally:
                loop.close()

        loop = asyncio.new_event_loop()
        executor.submit(run, loop)
        result = asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, loop=loop))

        def stop_loop(t: asyncio.Future[TResult]) -> None:
            async def loop_stop() -> bool:
                loop.stop()
                return True

            asyncio.run_coroutine_threadsafe(loop_stop(), loop=loop)

        result.add_done_callback(stop_loop)
        return result

    async def _notify(  # type: ignore
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> AsyncGenerator[TResult, None]:
        def _done(f: asyncio.Future[TResult]) -> None:
            if result_callback is not None:
                try:
                    result_callback(f.result(), f.exception())
                except KeyboardInterrupt:
                    raise
                except BaseException as e:
                    result_callback(None, e)

        awaitables: List[asyncio.Future[TResult]] = []
        for method_listener in self.listeners:
            method = method_listener()
            if method is not None:
                future = self._run_in_asyncio_thread(self.executor, method(sender, param))
                if result_callback is not None:
                    future.add_done_callback(_done)
                awaitables.append(future)

        for a in await asyncio.gather(*awaitables, return_exceptions=True):
            if isinstance(a, BaseException) and self.ignore_exceptions:
                continue
            yield cast("TResult", a)


class AsyncThreadingEventGenerator(AsyncThreadingEventGeneratorBase[TSender, TParam, TResult]):
    def __call__(
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> "AsyncGenerator[TResult, None]":
        return self._notify(sender, param, result_callback=result_callback)


class AsyncThreadingEvent(AsyncThreadingEventGeneratorBase[TSender, TParam, TResult]):
    async def __call__(
        self,
        sender: TSender,
        param: TParam,
        *,
        result_callback: Optional[Callable[[Optional[TResult], Optional[BaseException]], Any]] = None,
    ) -> List[TResult]:
        return [e async for e in self._notify(sender, param, result_callback=result_callback)]
