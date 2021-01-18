import asyncio
import inspect
import weakref
import threading
from abc import ABC
from concurrent.futures.thread import ThreadPoolExecutor
from types import MethodType
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Generic,
    List,
    MutableSet,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from ..utils.inspect import ensure_coroutine

__all__ = [
    "AsyncEventIterator",
    "AsyncEvent",
    "async_event",
    "AsyncTaskingEventIterator",
    "AsyncTaskingEvent",
    "async_tasking_event_iterator",
    "async_tasking_event",
    "AsyncThreadingEventIterator",
    "AsyncThreadingEvent",
    "async_threading_event_iterator",
    "async_threading_event",
]

_TResult = TypeVar("_TResult")
_TCallable = TypeVar("_TCallable", bound=Callable[..., Union[Any, AsyncIterator[Any]]])


class AsyncEventResultIteratorBase(Generic[_TCallable, _TResult]):
    def __init__(self) -> None:
        self.lock = threading.RLock()

        self.listeners: MutableSet[weakref.ref[Any]] = set()

    def add(self, callback: _TCallable) -> None:
        async def remove_safe(ref: Any) -> None:
            with self.lock:
                self.listeners.remove(ref)

        def remove_listener(ref: Any) -> None:
            asyncio.ensure_future(remove_safe(ref))

        with self.lock:
            if inspect.ismethod(callback):
                self.listeners.add(weakref.WeakMethod(cast(MethodType, callback), remove_listener))
            else:
                self.listeners.add(weakref.ref(callback, remove_listener))

    def remove(self, callback: _TCallable) -> None:
        with self.lock:
            if inspect.ismethod(callback):
                self.listeners.remove(weakref.WeakMethod(cast(MethodType, callback)))
            else:
                self.listeners.remove(weakref.ref(callback))

    async def _notify(self, *args: Any, **kwargs: Any) -> AsyncIterator[_TResult]:
        for method_listener in self.listeners:
            method = method_listener()
            if method is not None:
                result = method(*args, **kwargs)
                if inspect.isawaitable(result):
                    result = await result

                yield result


class AsyncEventIterator(AsyncEventResultIteratorBase[_TCallable, _TResult]):
    def __call__(self, *args: Any, **kwargs: Any) -> AsyncIterator[_TResult]:
        return self._notify(*args, **kwargs)


class AsyncEvent(AsyncEventResultIteratorBase[_TCallable, _TResult]):
    async def __call__(self, *args: Any, **kwargs: Any) -> List[_TResult]:
        return [a async for a in self._notify(*args, **kwargs)]


_TEvent = TypeVar("_TEvent")


class AsyncEventDescriptorBase(Generic[_TCallable, _TResult, _TEvent]):
    def __init__(
        self, _func: _TCallable, factory: Callable[..., _TEvent], *factory_args: Any, **factory_kwargs: Any
    ) -> None:
        self._func = _func
        self.__factory = factory
        self.__event: Optional[_TEvent] = None
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

        if self.__event is None:
            self.__event = self.__factory(*self.__factory_args, **self.__factory_kwargs)

        return self.__event


class async_event_iterator(  # noqa: N801
    AsyncEventDescriptorBase[_TCallable, Any, AsyncEventIterator[_TCallable, Any]]
):
    def __init__(self, _func: _TCallable) -> None:
        super().__init__(_func, AsyncEventIterator[_TCallable, _TResult])


class async_event(AsyncEventDescriptorBase[_TCallable, Any, AsyncEvent[_TCallable, Any]]):  # noqa: N801
    def __init__(self, _func: _TCallable) -> None:
        super().__init__(_func, AsyncEvent[_TCallable, _TResult])


class AsyncTaskingEventResultIteratorBase(AsyncEventResultIteratorBase[_TCallable, _TResult], ABC):
    def __init__(self, *, task_name_prefix: Optional[str] = None) -> None:
        super().__init__()
        self._task_name_prefix = task_name_prefix or type(self).__qualname__

    async def _notify(  # type: ignore
        self,
        *args: Any,
        result_callback: Optional[Callable[[Optional[_TResult], Optional[BaseException]], Any]] = None,
        return_exceptions: Optional[bool] = True,
        **kwargs: Any,
    ) -> AsyncIterator[Union[_TResult, BaseException]]:
        def _done(f: asyncio.Future[_TResult]) -> None:
            if result_callback is not None:
                try:
                    result_callback(f.result(), f.exception())
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as e:
                    result_callback(None, e)

        awaitables: List[asyncio.Future[_TResult]] = []
        for method_listener in self.listeners:
            method = method_listener()
            if method is not None:
                future = asyncio.ensure_future(ensure_coroutine(method)(*args, **kwargs))
                if isinstance(future, asyncio.Task):
                    future.set_name(
                        f"{self._task_name_prefix() if callable(self._task_name_prefix) else self._task_name_prefix}"
                        f"->{method.__qualname__}(...)"
                    )
                if result_callback is not None:
                    future.add_done_callback(_done)
                awaitables.append(future)

        for a in asyncio.as_completed(awaitables):
            try:
                yield await a
            except asyncio.CancelledError as e:
                if not return_exceptions:
                    yield e
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                if not return_exceptions:
                    yield e
                else:
                    raise


class AsyncTaskingEventIterator(AsyncTaskingEventResultIteratorBase[_TCallable, _TResult]):
    def __call__(self, *args: Any, **kwargs: Any) -> AsyncIterator[Union[_TResult, BaseException]]:
        return self._notify(*args, **kwargs)


def _get_name_prefix(descriptor: AsyncEventDescriptorBase[Any, Any, Any]) -> str:
    if descriptor._owner is None:
        return type(descriptor).__qualname__

    return f"{descriptor._owner.__qualname__}.{descriptor._owner_name}"


class async_tasking_event_iterator(  # noqa: N801
    AsyncEventDescriptorBase[_TCallable, Any, AsyncTaskingEventIterator[_TCallable, Any]]
):
    def __init__(self, _func: _TCallable) -> None:
        super().__init__(
            _func, AsyncTaskingEventIterator[_TCallable, Any], task_name_prefix=lambda: _get_name_prefix(self)
        )


class AsyncTaskingEvent(AsyncTaskingEventResultIteratorBase[_TCallable, _TResult]):
    async def __call__(self, *args: Any, **kwargs: Any) -> List[Union[_TResult, BaseException]]:
        return [a async for a in self._notify(*args, **kwargs)]


class async_tasking_event(AsyncEventDescriptorBase[_TCallable, Any, AsyncTaskingEvent[_TCallable, Any]]):  # noqa: N801
    def __init__(self, _func: _TCallable) -> None:
        super().__init__(_func, AsyncTaskingEvent[_TCallable, Any], task_name_prefix=lambda: _get_name_prefix(self))


class AsyncThreadingEventResultIteratorBase(AsyncEventResultIteratorBase[_TCallable, _TResult], ABC):
    __executor: Optional[ThreadPoolExecutor]

    def __init__(self, *, thread_name_prefix: Optional[str] = None) -> None:
        super().__init__()
        self.__executor = None
        self.__thread_name_prefix = thread_name_prefix or type(self).__qualname__

    def __del__(self) -> None:
        if self.__executor:
            self.__executor.shutdown(False)

    def _run_in_asyncio_thread(
        self,
        executor: ThreadPoolExecutor,
        coro: Union[asyncio.Future[_TResult], Awaitable[_TResult]],
        method_name: Optional[str] = None,
    ) -> asyncio.Future[_TResult]:
        def run(loop: asyncio.AbstractEventLoop) -> None:
            if method_name is not None:
                threading.current_thread().name = (
                    self.__thread_name_prefix() if callable(self.__thread_name_prefix) else self.__thread_name_prefix
                ) + f"->{method_name}(...)"

            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            finally:
                loop.close()

        loop = asyncio.new_event_loop()

        # loop.set_debug(True)

        executor.submit(run, loop)

        result = asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, loop=loop))

        def stop_loop(t: asyncio.Future[_TResult]) -> None:
            async def loop_stop() -> bool:
                loop.stop()
                return True

            asyncio.run_coroutine_threadsafe(loop_stop(), loop=loop)

        result.add_done_callback(stop_loop)
        return result

    async def _notify(  # type: ignore
        self,
        *args: Any,
        result_callback: Optional[Callable[[Optional[_TResult], Optional[BaseException]], Any]] = None,
        executor: Optional[ThreadPoolExecutor] = None,
        return_exceptions: Optional[bool] = True,
        **kwargs: Any,
    ) -> AsyncIterator[Union[_TResult, BaseException]]:
        def _done(f: asyncio.Future[_TResult]) -> None:
            if result_callback is not None:
                try:
                    result_callback(f.result(), f.exception())
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as e:
                    result_callback(None, e)

        if executor is None:
            if self.__executor is None:
                self.__executor = ThreadPoolExecutor(
                    thread_name_prefix=self.__thread_name_prefix()
                    if callable(self.__thread_name_prefix)
                    else self.__thread_name_prefix
                )
            executor = self.__executor

        awaitables: List[asyncio.Future[_TResult]] = []
        for method_listener in self.listeners:
            method = method_listener()
            if method is not None:
                future = self._run_in_asyncio_thread(
                    executor,
                    ensure_coroutine(method)(*args, **kwargs),
                    method.__qualname__,
                )
                if result_callback is not None:
                    future.add_done_callback(_done)
                awaitables.append(future)

        for a in asyncio.as_completed(awaitables):
            try:
                yield await a
            except asyncio.CancelledError as e:
                if not return_exceptions:
                    yield e
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                if not return_exceptions:
                    yield e
                else:
                    raise


class AsyncThreadingEventIterator(AsyncThreadingEventResultIteratorBase[_TCallable, _TResult]):
    def __call__(self, *args: Any, **kwargs: Any) -> AsyncIterator[Union[_TResult, BaseException]]:
        return self._notify(*args, **kwargs)


class async_threading_event_iterator(  # noqa: N801
    AsyncEventDescriptorBase[_TCallable, Any, AsyncThreadingEventIterator[_TCallable, Any]]
):
    def __init__(self, _func: _TCallable) -> None:
        super().__init__(
            _func, AsyncThreadingEventIterator[_TCallable, Any], thread_name_prefix=lambda: _get_name_prefix(self)
        )


class AsyncThreadingEvent(AsyncThreadingEventResultIteratorBase[_TCallable, _TResult]):
    async def __call__(self, *args: Any, **kwargs: Any) -> List[Union[_TResult, BaseException]]:
        return [a async for a in self._notify(*args, **kwargs)]


class async_threading_event(  # noqa: N801
    AsyncEventDescriptorBase[_TCallable, Any, AsyncThreadingEvent[_TCallable, Any]]
):
    def __init__(self, _func: _TCallable) -> None:
        super().__init__(_func, AsyncThreadingEvent[_TCallable, Any], thread_name_prefix=lambda: _get_name_prefix(self))
