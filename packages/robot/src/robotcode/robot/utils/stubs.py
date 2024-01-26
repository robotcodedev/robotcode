from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Protocol, Set, runtime_checkable


@runtime_checkable
class HasError(Protocol):
    error: Optional[str]


@runtime_checkable
class HasErrors(Protocol):
    errors: Optional[List[str]]


@runtime_checkable
class HeaderAndBodyBlock(Protocol):
    header: Any
    body: List[Any]


@runtime_checkable
class BodyBlock(Protocol):
    body: List[Any]


@runtime_checkable
class Languages(Protocol):
    languages: List[Any]
    headers: Dict[str, str]
    settings: Dict[str, str]
    bdd_prefixes: Set[str]
    true_strings: Set[str]
    false_strings: Set[str]

    def add_language(self, name: str) -> None: ...

    def __iter__(self) -> Iterator[Any]: ...
