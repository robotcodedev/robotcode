import inspect
from typing import Any, Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

__THREADED_MARKER = "__threaded__"


def threaded(enabled: bool = True) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, __THREADED_MARKER, enabled)
        return func

    return decorator


def is_threaded_callable(func: Callable[..., Any]) -> bool:
    return getattr(func, __THREADED_MARKER, False) or inspect.ismethod(func) and getattr(func, __THREADED_MARKER, False)
