from typing import Protocol, runtime_checkable

from robotcode.core.lsp.types import ServerCapabilities

__all__ = ["HasExtendCapabilities"]


@runtime_checkable
class HasExtendCapabilities(Protocol):
    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        ...
