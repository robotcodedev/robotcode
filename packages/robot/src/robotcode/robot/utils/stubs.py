from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable


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
