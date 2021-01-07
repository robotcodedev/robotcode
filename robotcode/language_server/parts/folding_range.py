from typing import Any, TYPE_CHECKING, Dict, List

from ...utils.logging import LoggingDescriptor
from ...utils.async_event import AsyncThreadingEvent
from ...jsonrpc2.protocol import rpc_method
from ..types import (
    DocumentUri,
    FoldingRange,
    FoldingRangeParams,
    TextDocumentIdentifier,
)

from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class FoldingRangeProtocolPart(LanguageServerProtocolPart):

    _logger = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}
        self.collect_folding_range_event = AsyncThreadingEvent[
            FoldingRangeProtocolPart, TextDocument, List[FoldingRange]
        ]()

    @rpc_method(name="textDocument/foldingRange", param_type=FoldingRangeParams)
    async def _text_document_folding_range(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> List[FoldingRange]:

        results: List[FoldingRange] = []

        for e in await self.collect_folding_range_event(self, self.parent.documents[text_document.uri]):
            results += e

        return results
