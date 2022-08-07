from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    FoldingRange,
    FoldingRangeParams,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol  # pragma: no cover

from .protocol_part import LanguageServerProtocolPart


class FoldingRangeProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

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

        if len(results) == 0:
            return None
        return results
