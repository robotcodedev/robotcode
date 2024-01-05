from __future__ import annotations

import asyncio
import atexit
import concurrent.futures
import contextvars
import functools
import threading
import time
import warnings
import weakref
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from types import TracebackType
from typing import (
    Any,
    Callable,
    Coroutine,
    Deque,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

_T = TypeVar("_T")


def check_canceled_sync() -> bool:
    info = get_current_future_info()
    if info is not None and info.canceled():
        raise asyncio.CancelledError
    return True


__executor = ThreadPoolExecutor(thread_name_prefix="global_sub_asyncio")


def shutdown_thread_pool_executor() -> None:
    __executor.shutdown(wait=False)


atexit.register(shutdown_thread_pool_executor)


def run_in_thread(func: Callable[..., _T], /, *args: Any, **kwargs: Any) -> asyncio.Future[_T]:
    loop = asyncio.get_running_loop()

    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)

    return cast(
        "asyncio.Future[_T]",
        loop.run_in_executor(__executor, cast(Callable[..., _T], func_call)),
    )

    # executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sub_asyncio")
    # try:
    #     return cast(
    #         "asyncio.Future[_T]",
    #         loop.run_in_executor(executor, cast(Callable[..., _T], func_call)),
    #     )
    # finally:
    #     executor.shutdown(wait=False)


def run_coroutine_in_thread(
    coro: Callable[..., Coroutine[Any, Any, _T]], *args: Any, **kwargs: Any
) -> asyncio.Future[_T]:
    callback_added_event = threading.Event()
    inner_task: Optional[asyncio.Task[_T]] = None
    canceled = False
    result: Optional[asyncio.Future[_T]] = None

    async def create_inner_task(coro: Callable[..., Coroutine[Any, Any, _T]], *args: Any, **kwargs: Any) -> _T:
        nonlocal inner_task

        ct = asyncio.current_task()

        loop = asyncio.get_event_loop()
        loop.slow_callback_duration = 10

        callback_added_event.wait(600)

        if ct is not None and result is not None:
            _running_tasks[result].children.add(ct)

        inner_task = create_sub_task(coro(*args, **kwargs), name=coro.__qualname__)

        if canceled:
            inner_task.cancel()

        return await inner_task

    def run(coro: Callable[..., Coroutine[Any, Any, _T]], *args: Any, **kwargs: Any) -> _T:
        old_name = threading.current_thread().name
        threading.current_thread().name = coro.__qualname__
        try:
            return asyncio.run(create_inner_task(coro, *args, **kwargs))
        finally:
            threading.current_thread().name = old_name

    cti = get_current_future_info()
    result = run_in_thread(run, coro, *args, **kwargs)

    _running_tasks[result] = FutureInfo(result)
    if cti is not None:
        cti.children.add(result)

    def done(task: asyncio.Future[_T]) -> None:
        nonlocal canceled

        canceled = task.cancelled()

        if canceled and inner_task is not None and not inner_task.done():
            inner_task.get_loop().call_soon_threadsafe(inner_task.cancel)

    result.add_done_callback(done)

    callback_added_event.set()

    return result


class Event:
    """Thread safe version of an async Event"""

    def __init__(self, value: bool = False) -> None:
        self._waiters: Deque[asyncio.Future[Any]] = deque()
        self._value = [value]  # make value atomic according to GIL

    def __repr__(self) -> str:
        res = super().__repr__()
        extra = "set" if self._value else "unset"
        if self._waiters:
            extra = f"{extra}, waiters:{len(self._waiters)}"
        return f"<{res[1:-1]} [{extra}]>"

    def is_set(self) -> bool:
        return self._value[0]

    def set(self) -> None:
        if not self._value[0]:
            self._value[0] = True

            while self._waiters:
                fut = self._waiters.popleft()

                if not fut.done():
                    if fut.get_loop() == asyncio.get_running_loop():
                        if not fut.done():
                            fut.set_result(True)
                    else:

                        def set_result(w: asyncio.Future[Any], ev: threading.Event) -> None:
                            try:
                                if not w.done():
                                    w.set_result(True)
                            finally:
                                ev.set()

                        done = threading.Event()

                        fut.get_loop().call_soon_threadsafe(set_result, fut, done)

                        start = time.monotonic()
                        while not done.is_set():
                            check_canceled_sync()

                            if time.monotonic() - start > 120:
                                warnings.warn("Can't set future result.")
                                break

                            time.sleep(0.001)

    def clear(self) -> None:
        self._value[0] = False

    async def wait(self, timeout: Optional[float] = None) -> bool:
        if self._value[0]:
            return True

        fut = create_sub_future()
        self._waiters.append(fut)

        try:
            await asyncio.wait_for(fut, timeout)
            return True
        except asyncio.TimeoutError:
            return False


class Lock:
    """Threadsafe version of an async Lock."""

    def __init__(self) -> None:
        self._waiters: Optional[Deque[asyncio.Future[Any]]] = None
        self._locked = [False]  # make locked atomic according to GIL
        self._locker: Optional[asyncio.Task[Any]] = None

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()

    def __repr__(self) -> str:
        res = super().__repr__()
        extra = "locked" if self._locked else "unlocked"
        if self._waiters:
            extra = f"{extra}, waiters:{len(self._waiters)}"
        return f"<{res[1:-1]} [{extra}]> {self._locker}"

    @property
    def locked(self) -> bool:
        return self._locked[0]

    def _set_locked(self, value: bool) -> None:
        self._locked[0] = value
        self._locker = asyncio.current_task() if value else None

    async def acquire(self) -> bool:
        if not self.locked and (self._waiters is None or all(w.cancelled() for w in self._waiters)):
            self._set_locked(True)

            return True

        if self._waiters is None:
            self._waiters = deque()

        fut = create_sub_future()
        self._waiters.append(fut)

        try:
            try:

                def aaa(fut: asyncio.Future[Any]) -> None:
                    warnings.warn(f"Lock {self} takes to long {threading.current_thread()}\n, try to cancel...")
                    fut.cancel()

                h = fut.get_loop().call_later(60, aaa, fut)
                try:
                    await fut
                finally:
                    h.cancel()
            finally:
                self._waiters.remove(fut)
        except asyncio.CancelledError:
            if not self.locked:
                self._wake_up_first()
            raise

        self._set_locked(True)

        return True

    def release(self) -> None:
        if self.locked:
            self._set_locked(False)
            self._wake_up_first()
        else:
            raise RuntimeError("Lock is not acquired.")

    def _wake_up_first(self) -> None:
        if not self._waiters:
            return

        try:
            fut = next(iter(self._waiters))
        except StopIteration:
            return

        if fut.get_loop().is_running() and not fut.get_loop().is_closed():
            if fut.get_loop() == asyncio.get_running_loop():
                if not fut.done():
                    fut.set_result(True)
            else:

                def set_result(w: asyncio.Future[Any], ev: threading.Event) -> None:
                    try:
                        if w.get_loop().is_running() and not w.done():
                            w.set_result(True)
                    finally:
                        ev.set()

                if not fut.done():
                    done = threading.Event()

                    fut.get_loop().call_soon_threadsafe(set_result, fut, done)

                    start = time.monotonic()
                    while not done.is_set():
                        if time.monotonic() - start > 120:
                            warnings.warn("Can't set future result.")
                            break

                        time.sleep(0.001)
        else:
            warnings.warn(f"Future {fut!r} loop is closed")
            self._waiters.remove(fut)
            self._wake_up_first()


_global_futures_set: Set[asyncio.Future[Any]] = set()


class FutureInfo:
    def __init__(self, future: asyncio.Future[Any]) -> None:
        self.task: weakref.ref[asyncio.Future[Any]] = weakref.ref(future)
        self.children: weakref.WeakSet[asyncio.Future[Any]] = weakref.WeakSet()
        _global_futures_set.add(future)
        future.add_done_callback(self._done)

    def _done(self, future: asyncio.Future[Any]) -> None:
        _global_futures_set.discard(future)

        if future.cancelled():
            for t in self.children.copy():
                if not t.done() and not t.cancelled() and t.get_loop().is_running():
                    if t.get_loop() == asyncio.get_running_loop():
                        t.cancel()
                    else:
                        t.get_loop().call_soon_threadsafe(t.cancel)

    def canceled(self) -> bool:
        task = self.task()
        if task is not None and task.cancelled():
            return True
        return False


_running_tasks: weakref.WeakKeyDictionary[asyncio.Future[Any], FutureInfo] = weakref.WeakKeyDictionary()


def get_current_future_info() -> Optional[FutureInfo]:
    try:
        ct = asyncio.current_task()

        if ct is None:
            return None
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException:
        return None

    if ct not in _running_tasks:
        _running_tasks[ct] = FutureInfo(ct)

    return _running_tasks[ct]


def create_sub_task(
    coro: Coroutine[Any, Any, _T],
    *,
    name: Optional[str] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> asyncio.Task[_T]:
    ct = get_current_future_info()

    if loop is not None:
        if loop == asyncio.get_running_loop():
            result = loop.create_task(coro, name=name)
        else:

            async def create_task(
                lo: asyncio.AbstractEventLoop,
                c: Coroutine[Any, Any, _T],
                n: Optional[str],
            ) -> asyncio.Task[_T]:
                return create_sub_task(c, name=n, loop=lo)

            return asyncio.run_coroutine_threadsafe(create_task(loop, coro, name), loop=loop).result()
    else:
        result = asyncio.create_task(coro, name=name)

    if ct is not None:
        ct.children.add(result)

    _running_tasks[result] = FutureInfo(result)
    return result


def create_sub_future(
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> asyncio.Future[Any]:
    ct = get_current_future_info()

    if loop is None:
        loop = asyncio.get_running_loop()

    result = loop.create_future()

    _running_tasks[result] = FutureInfo(result)

    if ct is not None:
        ct.children.add(result)

    return result


def run_coroutine_from_thread_as_future(
    func: Callable[..., Coroutine[Any, Any, _T]],
    *args: Any,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    **kwargs: Any,
) -> asyncio.Future[_T]:
    if loop is None:
        loop = asyncio.get_running_loop()

    return wrap_sub_future(asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop))


async def run_coroutine_from_thread_async(
    func: Callable[..., Coroutine[Any, Any, _T]],
    *args: Any,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    **kwargs: Any,
) -> _T:
    if loop is None:
        loop = asyncio.get_running_loop()

    return await run_coroutine_from_thread_as_future(func, *args, loop=loop, **kwargs)


def wrap_sub_future(
    future: Union[asyncio.Future[_T], concurrent.futures.Future[_T]],
    *,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> asyncio.Future[_T]:
    result = asyncio.wrap_future(future, loop=loop)
    ci = get_current_future_info()
    if ci is not None:
        ci.children.add(result)
    return result
