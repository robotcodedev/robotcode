from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional, Union

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    DeclarationParams,
    Location,
    LocationLink,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class DeclarationProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self.link_support = False

    @async_tasking_event
    async def collect(
        sender, document: TextDocument, position: Position  # NOSONAR
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.text_document is not None
            and self.parent.client_capabilities.text_document.declaration
        ):
            self.link_support = self.parent.client_capabilities.text_document.declaration.link_support or False

        if len(self.collect):
            capabilities.declaration_provider = True

    @rpc_method(name="textDocument/declaration", param_type=DeclarationParams)
    @threaded()
    async def _text_document_declaration(
        self, text_document: TextDocumentIdentifier, position: Position, *args: Any, **kwargs: Any
    ) -> Optional[Union[Location, List[Location], List[LocationLink]]]:

        locations: List[Location] = []
        location_links: List[LocationLink] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(self, document, position, callback_filter=language_id_filter(document)):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    if isinstance(result, Location):
                        locations.append(result)
                    else:
                        for e in result:
                            if isinstance(e, Location):
                                locations.append(e)
                            elif isinstance(e, LocationLink):
                                location_links.append(e)
        if len(locations) == 0 and len(location_links) == 0:
            return None

        if len(locations) > 0 and len(location_links) == 0:
            if len(locations) == 1:
                return locations[0]
            else:
                return locations

        if len(locations) > 0 and len(location_links) > 0:
            self._logger.warning("can't mix Locations and LocationLinks")

        if self.link_support:
            return location_links

        self._logger.warning("client has no link_support capability, convert LocationLinks to Location")

        return [Location(uri=e.target_uri, range=e.target_range) for e in location_links]
