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
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    DocumentSymbol,
    DocumentSymbolClientCapabilitiesSymbolKindType,
    DocumentSymbolClientCapabilitiesTagSupportType,
    DocumentSymbolOptions,
    DocumentSymbolParams,
    ServerCapabilities,
    SymbolInformation,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
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


class DocumentSymbolsProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.hierarchical_document_symbol_support = False
        self.symbol_kind: Optional[DocumentSymbolClientCapabilitiesSymbolKindType] = None
        self.tag_support: Optional[DocumentSymbolClientCapabilitiesTagSupportType] = None

    @event
    def collect(
        sender,
        document: TextDocument,
    ) -> Optional[Union[List[DocumentSymbol], List[SymbolInformation], None]]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.text_document
            and self.parent.client_capabilities.text_document.document_symbol
        ):
            document_symbol = self.parent.client_capabilities.text_document.document_symbol

            label_suppport = document_symbol.label_support or False
            self.hierarchical_document_symbol_support = document_symbol.hierarchical_document_symbol_support or False
            self.symbol_kind = document_symbol.symbol_kind
            self.tag_support = document_symbol.tag_support

            if len(self.collect):
                if label_suppport:
                    label = (
                        cast(HasSymbolInformationLabel, self.parent).symbol_information_label
                        if isinstance(self.parent, HasSymbolInformationLabel)
                        else None
                    )

                    capabilities.document_symbol_provider = (
                        DocumentSymbolOptions(label=label) if label else DocumentSymbolOptions()
                    )
                else:
                    capabilities.document_symbol_provider = True

    @rpc_method(name="textDocument/documentSymbol", param_type=DocumentSymbolParams, threaded=True)
    def _text_document_symbol(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> Optional[Union[List[DocumentSymbol], List[SymbolInformation], None]]:
        document_symbols: List[DocumentSymbol] = []
        symbol_informations: List[SymbolInformation] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(self, document, callback_filter=language_id_filter(document)):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    if all(isinstance(e, DocumentSymbol) for e in result):
                        document_symbols.extend(cast(Iterable[DocumentSymbol], result))
                    elif all(isinstance(e, SymbolInformation) for e in result):
                        symbol_informations.extend(cast(Iterable[SymbolInformation], result))
                    else:
                        self._logger.warning(
                            "Result contains DocumentSymbol and SymbolInformation results, result is skipped."
                        )
        if document_symbols:

            def traverse(symbol: DocumentSymbol, doc: TextDocument) -> None:
                symbol.range = doc.range_to_utf16(symbol.range)
                symbol.selection_range = doc.range_to_utf16(symbol.selection_range)
                for child in symbol.children or []:
                    traverse(child, doc)

            for symbol in document_symbols:
                traverse(symbol, document)

        if symbol_informations:
            for symbol_information in symbol_informations:
                doc = self.parent.documents.get(symbol_information.location.uri)
                if doc is not None:
                    symbol_information.location.range = doc.range_to_utf16(symbol_information.location.range)

        if document_symbols and symbol_informations:
            self._logger.warning(
                "Result contains DocumentSymbol and SymbolInformation results, only DocumentSymbols returned."
            )
            return document_symbols

        if document_symbols:
            return document_symbols

        if symbol_informations:
            return symbol_informations

        return None
