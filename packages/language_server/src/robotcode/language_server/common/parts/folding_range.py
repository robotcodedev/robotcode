from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    FoldingRange,
    FoldingRangeParams,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import (
        LanguageServerProtocol,
    )


class FoldingRangeProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    @event
    def collect(sender, document: TextDocument) -> Optional[List[FoldingRange]]:  # pragma: no cover, NOSONAR
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.folding_range_provider = True

    @rpc_method(name="textDocument/foldingRange", param_type=FoldingRangeParams, threaded=True)
    def _text_document_folding_range(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> Optional[List[FoldingRange]]:
        results: List[FoldingRange] = []
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(self, document, callback_filter=language_id_filter(document)):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if not results:
            return None

        for r in results:
            if r.start_character is not None:
                r.start_character = document.position_to_utf16(Position(r.start_line, r.start_character)).character
            if r.end_character is not None:
                r.end_character = document.position_to_utf16(Position(r.end_line, r.end_character)).character

        return results
