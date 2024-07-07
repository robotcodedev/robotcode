import contextlib
import inspect
import os
import threading
from concurrent.futures import CancelledError, Future
from types import TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    cast,
    overload,
)

from typing_extensions import ParamSpec, Self


class Lockable(Protocol):
    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool: ...

    def release(self) -> None: ...

    def __enter__(self) -> bool: ...

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None: ...

    def __str__(self) -> str: ...


class LockBase:
    def __init__(
        self,
        lock: Lockable,
        default_timeout: Optional[float] = None,
        name: Optional[str] = None,
    ) -> None:
        self._default_timeout = default_timeout
        self.name = name
        self._lock = threading.RLock()

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        timeout = timeout if timeout is not None else self._default_timeout or -1
        aquired = self._lock.acquire(blocking, timeout=timeout)
        if not aquired and blocking and timeout > 0:
            raise RuntimeError(
                f"Could not acquire {self.__class__.__qualname__} {self.name+' ' if self.name else ' '}in {timeout}s."
            )
        return aquired

    def release(self) -> None:
        return self._lock.release()

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        return self.release()

    def __str__(self) -> str:
        return self._lock.__str__()

    @contextlib.contextmanager
    def __call__(self, *, timeout: Optional[float] = None) -> Iterator["Self"]:
        aquired = self.acquire(timeout=timeout)
        try:
            yield self
        finally:
            if aquired:
                self.release()


class RLock(LockBase):
    def __init__(
        self,
        default_timeout: Optional[float] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(threading.RLock(), default_timeout=default_timeout, name=name)


class Lock(LockBase):
    def __init__(
        self,
        default_timeout: Optional[float] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(threading.Lock(), default_timeout=default_timeout, name=name)


_F = TypeVar("_F", bound=Callable[..., Any])
_TResult = TypeVar("_TResult")

__THREADED_MARKER = "__robotcode_threaded"


class Task(Future, Generic[_TResult]):  # type: ignore[type-arg]
    def __init__(self) -> None:
        super().__init__()
        self.cancelation_requested_event = threading.Event()

    @property
    def cancelation_requested(self) -> bool:
        return self.cancelation_requested_event.is_set()

    def cancel(self) -> bool:
        self.cancelation_requested_event.set()
        return super().cancel()

    def result(self, timeout: Optional[float] = None) -> _TResult:
        return cast(_TResult, super().result(timeout))

    def add_done_callback(self, fn: Callable[["Task[Any]"], Any]) -> None:
        super().add_done_callback(fn)  # type: ignore[arg-type]


@overload
def threaded_task(__func: _F) -> _F: ...


@overload
def threaded_task(*, enabled: bool = True) -> Callable[[_F], _F]: ...


def threaded_task(__func: _F = None, *, enabled: bool = True) -> Callable[[_F], _F]:
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


class _Local(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self._local_future: Optional[Task[Any]] = None


_local_storage = _Local()


def _run_task_in_thread_handler(
    future: Task[_TResult],
    callable: Callable[..., _TResult],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
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


def is_current_task_cancelled() -> bool:
    local_future = _local_storage._local_future
    return local_future is not None and local_future.cancelation_requested


def check_current_task_canceled(at_least_seconds: Optional[float] = None, raise_exception: bool = True) -> bool:
    local_future = _local_storage._local_future
    if local_future is None:
        return False

    if at_least_seconds is None or at_least_seconds <= 0:
        if not local_future.cancelation_requested:
            return False
    elif not local_future.cancelation_requested_event.wait(at_least_seconds):
        return False

    if raise_exception:
        name = threading.current_thread().name
        raise CancelledError(f"Thread {name + ' ' if name else ' '}cancelled")

    return True


_running_tasks_lock = RLock()
_running_tasks: Dict[Task[Any], threading.Thread] = {}


def _remove_future_from_running_tasks(future: Task[Any]) -> None:
    with _running_tasks_lock:
        _running_tasks.pop(future, None)


_P = ParamSpec("_P")


def _create_task_in_thread(
    callable: Callable[_P, _TResult], *args: _P.args, **kwargs: _P.kwargs
) -> Tuple[Task[_TResult], threading.Thread]:
    future: Task[_TResult] = Task()
    with _running_tasks_lock:
        thread = threading.Thread(
            target=_run_task_in_thread_handler,
            args=(future, callable, args, kwargs),
            name=str(callable),
        )
        _running_tasks[future] = thread
        future.add_done_callback(_remove_future_from_running_tasks)

    # TODO: don't set daemon=True because it can be deprecated in future pyhton versions
    thread.daemon = True
    return future, thread


def run_as_task(callable: Callable[_P, _TResult], *args: _P.args, **kwargs: _P.kwargs) -> Task[_TResult]:
    future, thread = _create_task_in_thread(callable, *args, **kwargs)

    thread.start()

    return future


def run_as_debugpy_hidden_task(callable: Callable[_P, _TResult], *args: _P.args, **kwargs: _P.kwargs) -> Task[_TResult]:
    future, thread = _create_task_in_thread(callable, *args, **kwargs)

    hidden_tasks = os.environ.get("ROBOTCODE_DISABLE_HIDDEN_TASKS", "0")
    hide = hidden_tasks == "0"

    if hide:
        thread.pydev_do_not_trace = True  # type: ignore[attr-defined]
        thread.is_pydev_daemon_thread = True  # type: ignore[attr-defined]

    thread.start()

    return future


def _cancel_all_running_tasks(timeout: Optional[float] = None) -> None:
    threads: List[threading.Thread] = []
    with _running_tasks_lock:
        for future, thread in _running_tasks.items():
            if not future.cancelation_requested:
                future.cancel()
                threads.append(thread)
    for thread in threads:
        if thread is not threading.current_thread():
            thread.join(timeout=timeout)
