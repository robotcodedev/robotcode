from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    LinkedEditingRangeOptions,
    LinkedEditingRangeParams,
    LinkedEditingRanges,
    Position,
    Range,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class LinkedEditingRangeProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.linked_editing_range_provider = LinkedEditingRangeOptions(work_done_progress=True)

    @async_tasking_event
    async def collect(sender, document: TextDocument, position: Position) -> Optional[LinkedEditingRanges]:  # NOSONAR
        ...

    @rpc_method(name="textDocument/linkedEditingRange", param_type=LinkedEditingRangeParams)
    @threaded()
    async def _text_document_linked_editing_range(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[LinkedEditingRanges]:

        linked_ranges: List[Range] = []
        word_pattern: Optional[str] = None

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(self, document, position, callback_filter=language_id_filter(document)):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    linked_ranges.extend(result.ranges)
                    if result.word_pattern is not None:
                        word_pattern = result.word_pattern

        return LinkedEditingRanges(linked_ranges, word_pattern)
