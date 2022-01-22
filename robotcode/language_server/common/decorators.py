from typing import Any, Callable, List, Protocol, TypeVar, runtime_checkable

from robotcode.language_server.common.text_document import TextDocument

_F = TypeVar("_F", bound=Callable[..., Any])


def language_id(id: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__language_id__", id)
        return func

    return decorator


@runtime_checkable
class HasLanguageId(Protocol):
    __language_id__: str


def trigger_characters(characters: List[str]) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__trigger_characters__", characters)
        return func

    return decorator


@runtime_checkable
class HasRetriggerCharacters(Protocol):
    __retrigger_characters__: str


def retrigger_characters(characters: List[str]) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__retrigger_characters__", characters)
        return func

    return decorator


@runtime_checkable
class HasTriggerCharacters(Protocol):
    __trigger_characters__: List[str]


def all_commit_characters(characters: List[str]) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__all_commit_characters__", characters)
        return func

    return decorator


@runtime_checkable
class HasAllCommitCharacters(Protocol):
    __all_commit_characters__: List[str]


def language_id_filter(document: TextDocument) -> Callable[[Any], bool]:
    def filter(c: Any) -> bool:
        return not isinstance(c, HasLanguageId) or c.__language_id__ == document.language_id

    return filter
