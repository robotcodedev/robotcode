from concurrent.futures import CancelledError
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Final,
    Iterable,
    List,
    Optional,
    Protocol,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

from robotcode.core.event import event
from robotcode.core.lsp.types import (
    Location,
    ServerCapabilities,
    SymbolInformation,
    WorkspaceSymbol,
    WorkspaceSymbolClientCapabilitiesResolveSupportType,
    WorkspaceSymbolClientCapabilitiesSymbolKindType,
    WorkspaceSymbolClientCapabilitiesTagSupportType,
    WorkspaceSymbolParams,
)
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


@runtime_checkable
class HasSymbolInformationLabel(Protocol):
    symbol_information_label: str


_F = TypeVar("_F", bound=Callable[..., Any])


def symbol_information_label(label: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "symbol_information_label", label)
        return func

    return decorator


class WorkspaceSymbolsProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.symbol_kind: Optional[WorkspaceSymbolClientCapabilitiesSymbolKindType] = None
        self.tag_support: Optional[WorkspaceSymbolClientCapabilitiesTagSupportType] = None
        self.resolve_support: Optional[WorkspaceSymbolClientCapabilitiesResolveSupportType] = None

    @event
    def collect(
        sender,
        query: str,
    ) -> Optional[Union[List[WorkspaceSymbol], List[SymbolInformation], None]]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.symbol is not None
        ):
            workspace_symbol = self.parent.client_capabilities.workspace.symbol

            self.symbol_kind = workspace_symbol.symbol_kind
            self.tag_support = workspace_symbol.tag_support
            self.resolve_support = workspace_symbol.resolve_support

            if len(self.collect):
                # TODO: Implement workspace resolve
                capabilities.workspace_symbol_provider = True

    @rpc_method(name="workspace/symbol", param_type=WorkspaceSymbolParams, threaded=True)
    def _workspace_symbol(
        self, query: str, *args: Any, **kwargs: Any
    ) -> Optional[Union[List[WorkspaceSymbol], List[SymbolInformation], None]]:
        workspace_symbols: List[WorkspaceSymbol] = []
        symbol_informations: List[SymbolInformation] = []

        for result in self.collect(self, query):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    if all(isinstance(e, WorkspaceSymbol) for e in result):
                        workspace_symbols.extend(cast(Iterable[WorkspaceSymbol], result))
                    elif all(isinstance(e, SymbolInformation) for e in result):
                        symbol_informations.extend(cast(Iterable[SymbolInformation], result))
                    else:
                        self._logger.warning(
                            "Result contains WorkspaceSymbol and SymbolInformation results, result is skipped."
                        )

        if workspace_symbols:
            for symbol in workspace_symbols:
                if isinstance(symbol.location, Location):
                    doc = self.parent.documents.get(symbol.location.uri)
                    if doc is not None:
                        symbol.location.range = doc.range_to_utf16(symbol.location.range)

        if symbol_informations:
            for symbol_information in symbol_informations:
                doc = self.parent.documents.get(symbol_information.location.uri)
                if doc is not None:
                    symbol_information.location.range = doc.range_to_utf16(symbol_information.location.range)

        if workspace_symbols and symbol_informations:
            self._logger.warning(
                "Result contains WorksapceSymbol and SymbolInformation results, only WorkspaceSymbols returned."
            )
            return workspace_symbols

        if workspace_symbols:
            return workspace_symbols

        if symbol_informations:
            return symbol_informations

        return None
