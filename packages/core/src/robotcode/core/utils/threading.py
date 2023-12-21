from typing import Any, Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])


def threaded(enabled: bool = True) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__threaded__", enabled)
        return func

    return decorator


def is_threaded_callable(func: Callable[..., Any]) -> bool:
    return getattr(func, "__threaded__", False)
