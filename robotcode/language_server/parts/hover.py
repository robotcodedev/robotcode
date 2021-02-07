from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ...jsonrpc2.protocol import rpc_method
from ...utils.async_event import async_tasking_event
from ...utils.logging import LoggingDescriptor
from ..has_extend_capabilities import HasExtendCapabilities
from ..language import HasLanguageId
from ..text_document import TextDocument
from ..types import DocumentUri, Hover, HoverParams, Position, ServerCapabilities, TextDocumentIdentifier

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class HoverProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}

    @async_tasking_event
    async def collect(sender, document: TextDocument, position: Position) -> Optional[Hover]:
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect.listeners):
            capabilities.hover_provider = True

    @rpc_method(name="textDocument/hover", param_type=HoverParams)
    async def _text_document_hover(
        self, text_document: TextDocumentIdentifier, position: Position, *args: Any, **kwargs: Any
    ) -> Optional[Hover]:

        results: List[Hover] = []
        document = self.parent.documents[text_document.uri]
        for result in await self.collect(
            self,
            document,
            position,
            callback_filter=lambda c: not isinstance(c, HasLanguageId) or c.__language_id__ == document.language_id,
        ):
            if isinstance(result, BaseException):
                self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if len(results) > 0:
            # TODO: can we combine hover results?
            if results[-1].contents:
                return results[-1]

        return None
