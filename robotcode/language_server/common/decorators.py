from typing import Any, Callable, List, Protocol, Set, TypeVar, Union, runtime_checkable

from .text_document import TextDocument

_F = TypeVar("_F", bound=Callable[..., Any])


def language_id(id: str, *ids: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__language_id__", {id, *ids})
        return func

    return decorator


@runtime_checkable
class HasLanguageId(Protocol):
    __language_id__: Set[str]


def trigger_characters(characters: List[str]) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__trigger_characters__", characters)
        return func

    return decorator


@runtime_checkable
class HasTriggerCharacters(Protocol):
    __trigger_characters__: List[str]


@runtime_checkable
class HasRetriggerCharacters(Protocol):
    __retrigger_characters__: str


def retrigger_characters(characters: List[str]) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__retrigger_characters__", characters)
        return func

    return decorator


def all_commit_characters(characters: List[str]) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__all_commit_characters__", characters)
        return func

    return decorator


@runtime_checkable
class HasAllCommitCharacters(Protocol):
    __all_commit_characters__: List[str]


def code_action_kinds(characters: List[str]) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__code_action_kinds__", characters)
        return func

    return decorator


@runtime_checkable
class HasCodeActionKinds(Protocol):
    __code_action_kinds__: List[str]


def language_id_filter(language_id_or_document: Union[str, TextDocument]) -> Callable[[Any], bool]:
    def filter(c: Any) -> bool:
        return not isinstance(c, HasLanguageId) or (
            (
                language_id_or_document.language_id
                if isinstance(language_id_or_document, TextDocument)
                else language_id_or_document
            )
            in c.__language_id__
        )

    return filter


@runtime_checkable
class IsCommand(Protocol):
    __command_name__: str


def command(name: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__command_name__", name)
        return func

    return decorator


def get_command_name(func: _F) -> str:
    if isinstance(func, IsCommand):
        return func.__command_name__

    raise TypeError(f"{func} is not a command.")
