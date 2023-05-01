from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.async_tools import async_tasking_event, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    FoldingRange,
    FoldingRangeParams,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import language_id_filter
from robotcode.language_server.common.has_extend_capabilities import HasExtendCapabilities
from robotcode.language_server.common.parts.protocol_part import LanguageServerProtocolPart
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol  # pragma: no cover


class FoldingRangeProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def collect(sender, document: TextDocument) -> Optional[List[FoldingRange]]:  # pragma: no cover, NOSONAR
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.folding_range_provider = True

    @rpc_method(name="textDocument/foldingRange", param_type=FoldingRangeParams)
    @threaded()
    async def _text_document_folding_range(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> Optional[List[FoldingRange]]:
        results: List[FoldingRange] = []
        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(self, document, callback_filter=language_id_filter(document)):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if not results:
            return None

        for result in results:
            if result.start_character is not None:
                result.start_character = document.position_to_utf16(
                    Position(result.start_line, result.start_character)
                ).character
            if result.end_character is not None:
                result.end_character = document.position_to_utf16(
                    Position(result.end_line, result.end_character)
                ).character

        return results
