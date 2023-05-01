from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.async_tools import async_tasking_event, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    Location,
    Position,
    ReferenceContext,
    ReferenceOptions,
    ReferenceParams,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import language_id_filter
from robotcode.language_server.common.has_extend_capabilities import HasExtendCapabilities
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class ReferencesProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.references_provider = ReferenceOptions(work_done_progress=True)

    @async_tasking_event
    async def collect(
        sender, document: TextDocument, position: Position, context: ReferenceContext  # NOSONAR
    ) -> Optional[List[Location]]:
        ...

    @rpc_method(name="textDocument/references", param_type=ReferenceParams)
    @threaded()
    async def _text_document_references(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        context: ReferenceContext,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[Location]]:
        await self.parent.diagnostics.ensure_workspace_loaded()

        locations: List[Location] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(
            self,
            document,
            document.position_from_utf16(position),
            context,
            callback_filter=language_id_filter(document),
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    locations.extend(result)

        if not locations:
            return None

        for location in locations:
            doc = await self.parent.documents.get(location.uri)
            if doc is not None:
                location.range = doc.range_to_utf16(location.range)

        return locations
