from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.async_tools import async_tasking_event, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    LinkedEditingRangeOptions,
    LinkedEditingRangeParams,
    LinkedEditingRanges,
    Position,
    Range,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import language_id_filter
from robotcode.language_server.common.has_extend_capabilities import (
    HasExtendCapabilities,
)
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class LinkedEditingRangeProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

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

        for result in await self.collect(
            self, document, document.position_from_utf16(position), callback_filter=language_id_filter(document)
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    linked_ranges.extend(result.ranges)
                    if result.word_pattern is not None:
                        word_pattern = result.word_pattern

        return LinkedEditingRanges([document.range_to_utf16(r) for r in linked_ranges], word_pattern)
