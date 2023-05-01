from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.async_tools import async_tasking_event, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    DocumentHighlight,
    DocumentHighlightOptions,
    DocumentHighlightParams,
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
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class DocumentHighlightProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.document_highlight_provider = DocumentHighlightOptions(work_done_progress=True)

    @async_tasking_event
    async def collect(
        sender, document: TextDocument, position: Position  # NOSONAR
    ) -> Optional[List[DocumentHighlight]]:
        ...

    @rpc_method(name="textDocument/documentHighlight", param_type=DocumentHighlightParams)
    @threaded()
    async def _text_document_document_highlight(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[DocumentHighlight]]:
        highlights: List[DocumentHighlight] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(
            self, document, document.position_from_utf16(position), callback_filter=language_id_filter(document)
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    highlights.extend(result)

        if len(highlights) == 0:
            return None

        for highlight in highlights:
            highlight.range = document.range_to_utf16(highlight.range)

        return highlights
