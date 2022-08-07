from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    DocumentHighlight,
    DocumentHighlightOptions,
    DocumentHighlightParams,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class DocumentHighlightProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

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

        for result in await self.collect(self, document, position, callback_filter=language_id_filter(document)):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    highlights.extend(result)

        if len(highlights) == 0:
            return None

        return highlights
