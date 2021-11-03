from typing import Protocol, runtime_checkable

from .lsp_types import ServerCapabilities

__all__ = ["HasExtendCapabilities"]


@runtime_checkable
class HasExtendCapabilities(Protocol):
    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        ...
