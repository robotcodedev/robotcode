import inspect
from concurrent.futures import CancelledError, Future
from threading import Event, Thread, current_thread, local
from typing import Any, Callable, Dict, Generic, Optional, Tuple, TypeVar, cast, overload

_F = TypeVar("_F", bound=Callable[..., Any])
_TResult = TypeVar("_TResult")

__THREADED_MARKER = "__threaded__"


class FutureEx(Future, Generic[_TResult]):  # type: ignore[type-arg]
    def __init__(self) -> None:
        super().__init__()
        self.cancelation_requested = Event()

    def cancel(self) -> bool:
        self.cancelation_requested.set()
        return super().cancel()

    def result(self, timeout: Optional[float] = None) -> _TResult:
        return cast(_TResult, super().result(timeout))


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
    _local_storage._local_future = future
    future.set_running_or_notify_cancel()
    try:
        result = callable(*args, **kwargs)
    except Exception as e:
        # TODO: add traceback to exception e.traceback = format_exc()
        if not future.cancelled():
            future.set_exception(e)
    else:
        if not future.cancelled():
            future.set_result(result)
    finally:
        _local_storage._local_future = None


def is_thread_cancelled() -> bool:
    local_future = _local_storage._local_future
    return local_future is not None and local_future.cancelation_requested.is_set()


def check_thread_canceled(at_least_seconds: Optional[float] = None) -> None:
    local_future = _local_storage._local_future
    if local_future is None:
        return

    if at_least_seconds is None or at_least_seconds <= 0:
        if not local_future.cancelation_requested.is_set():
            return
    elif not local_future.cancelation_requested.wait(at_least_seconds):
        return

    name = current_thread().name
    raise CancelledError(f"Thread {name+' ' if name else ' '}cancelled")


def run_callable_in_thread(callable: Callable[..., _TResult], *args: Any, **kwargs: Any) -> FutureEx[_TResult]:
    future: FutureEx[_TResult] = FutureEx()

    Thread(target=_run_callable_in_thread_handler, args=(future, callable, args, kwargs), name=str(callable)).start()

    return future
