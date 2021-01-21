from typing import Optional, TYPE_CHECKING, Any, Dict, List

from ...jsonrpc2.protocol import rpc_method
from ...utils.async_event import async_tasking_event
from ...utils.logging import LoggingDescriptor
from ..has_extend_capabilities import HasExtendCapabilities
from ..text_document import TextDocument
from ..types import DocumentUri, FoldingRange, FoldingRangeParams, ServerCapabilities, TextDocumentIdentifier

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class FoldingRangeProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}

    @async_tasking_event
    async def collect_folding_ranges(sender, document: TextDocument) -> Optional[List[FoldingRange]]:
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect_folding_ranges.listeners):
            capabilities.folding_range_provider = True

    @rpc_method(name="textDocument/foldingRange", param_type=FoldingRangeParams)
    async def _text_document_folding_range(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> Optional[List[FoldingRange]]:

        results: List[FoldingRange] = []

        for result in await self.collect_folding_ranges(self, self.parent.documents[text_document.uri]):
            if isinstance(result, BaseException):
                self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if len(results) == 0:
            return None
        return results
