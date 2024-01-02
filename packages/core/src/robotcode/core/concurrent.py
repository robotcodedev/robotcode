import inspect
from concurrent.futures import CancelledError, Future
from threading import Event, RLock, Thread, current_thread, local
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, cast, overload

_F = TypeVar("_F", bound=Callable[..., Any])
_TResult = TypeVar("_TResult")

__THREADED_MARKER = "__robotcode_threaded"


class FutureEx(Future, Generic[_TResult]):  # type: ignore[type-arg]
    def __init__(self) -> None:
        super().__init__()
        self.cancelation_requested_event = Event()

    @property
    def cancelation_requested(self) -> bool:
        return self.cancelation_requested_event.is_set()

    def cancel(self) -> bool:
        self.cancelation_requested_event.set()
        return super().cancel()

    def result(self, timeout: Optional[float] = None) -> _TResult:
        return cast(_TResult, super().result(timeout))

    def add_done_callback(self, fn: Callable[["FutureEx[Any]"], Any]) -> None:
        super().add_done_callback(fn)  # type: ignore[arg-type]


@overload
def threaded(__func: _F) -> _F:
    ...


@overload
def threaded(*, enabled: bool = True) -> Callable[[_F], _F]:
    ...


def threaded(__func: _F = None, *, enabled: bool = True) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, __THREADED_MARKER, enabled)
        return func

    if __func is not None:
        return decorator(__func)

    return decorator


def is_threaded_callable(callable: Callable[..., Any]) -> bool:
    return (
        getattr(callable, __THREADED_MARKER, False)
        or inspect.ismethod(callable)
        and getattr(callable, __THREADED_MARKER, False)
    )


class _Local(local):
    def __init__(self) -> None:
        super().__init__()
        self._local_future: Optional[FutureEx[Any]] = None


_local_storage = _Local()


def _run_callable_in_thread_handler(
    future: FutureEx[_TResult], callable: Callable[..., _TResult], args: Tuple[Any, ...], kwargs: Dict[str, Any]
) -> None:
    if not future.set_running_or_notify_cancel():
        return

    _local_storage._local_future = future

    try:
        result = callable(*args, **kwargs)
    except Exception as e:
        # TODO: add traceback to exception e.traceback = format_exc()
        future.set_exception(e)
    else:
        future.set_result(result)
    finally:
        _local_storage._local_future = None


def is_current_thread_cancelled() -> bool:
    local_future = _local_storage._local_future
    return local_future is not None and local_future.cancelation_requested


def check_current_thread_canceled(at_least_seconds: Optional[float] = None, raise_exception: bool = True) -> bool:
    local_future = _local_storage._local_future
    if local_future is None:
        return False

    if at_least_seconds is None or at_least_seconds <= 0:
        if not local_future.cancelation_requested:
            return False
    elif not local_future.cancelation_requested_event.wait(at_least_seconds):
        return False

    if raise_exception:
        name = current_thread().name
        raise CancelledError(f"Thread {name+' ' if name else ' '}cancelled")

    return True


_running_callables_lock = RLock()
_running_callables: Dict[FutureEx[Any], Thread] = {}


def _remove_future_from_running_callables(future: FutureEx[Any]) -> None:
    with _running_callables_lock:
        _running_callables.pop(future, None)


def run_in_thread(callable: Callable[..., _TResult], *args: Any, **kwargs: Any) -> FutureEx[_TResult]:
    future: FutureEx[_TResult] = FutureEx()
    with _running_callables_lock:
        thread = Thread(
            target=_run_callable_in_thread_handler, args=(future, callable, args, kwargs), name=str(callable)
        )
        _running_callables[future] = thread
        future.add_done_callback(_remove_future_from_running_callables)
    # TODO: don't set daemon=True because it can be deprecated in future pyhton versions
    thread.daemon = True
    thread.start()

    return future


def cancel_running_callables(timeout: Optional[float] = None) -> None:
    threads: List[Thread] = []
    with _running_callables_lock:
        for future, thread in _running_callables.items():
            if not future.cancelation_requested:
                future.cancel()
                threads.append(thread)
    for thread in threads:
        if thread is not current_thread():
            thread.join(timeout=timeout)
