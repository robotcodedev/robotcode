from typing import Any, Callable, Protocol, TypeVar, runtime_checkable


_F = TypeVar("_F", bound=Callable[..., Any])


def language_id(id: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__language_id__", id)
        return func

    return decorator


@runtime_checkable
class HasLanguageId(Protocol):
    __language_id__: str
