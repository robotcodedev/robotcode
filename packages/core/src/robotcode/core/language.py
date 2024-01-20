from dataclasses import dataclass
from typing import Any, Callable, List, Optional, TypeVar, Union

from robotcode.core.text_document import TextDocument

_F = TypeVar("_F", bound=Callable[..., Any])

LANGUAGE_ID_ATTR = "__language_id__"


def language_id(id: str, *ids: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, LANGUAGE_ID_ATTR, {id, *ids})
        return func

    return decorator


def language_id_filter(
    language_id_or_document: Union[str, TextDocument],
) -> Callable[[Any], bool]:
    def filter(c: Any) -> bool:
        return not hasattr(c, LANGUAGE_ID_ATTR) or (
            (
                language_id_or_document.language_id
                if isinstance(language_id_or_document, TextDocument)
                else language_id_or_document
            )
            in getattr(c, LANGUAGE_ID_ATTR)
        )

    return filter


@dataclass
class LanguageDefinition:
    id: str
    extensions: List[str]
    extensions_ignore_case: bool = False
    aliases: Optional[List[str]] = None
