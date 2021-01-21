from typing import Optional, TYPE_CHECKING, Any, Dict, List, Union

from ...jsonrpc2.protocol import rpc_method
from ...utils.async_event import async_tasking_event
from ...utils.logging import LoggingDescriptor
from ..has_extend_capabilities import HasExtendCapabilities
from ..text_document import TextDocument
from ..types import (
    DocumentUri,
    LocationLink,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
    DefinitionParams,
    Location,
)

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class DefinitionProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}
        self.link_support = False

    @async_tasking_event
    async def collect_definitions(
        sender, document: TextDocument, position: Position
    ) -> Optional[Union[Location, List[Location], List[LocationLink]]]:
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.text_document is not None
            and self.parent.client_capabilities.text_document.definition
        ):
            self.link_support = self.parent.client_capabilities.text_document.definition.link_support or False

        if len(self.collect_definitions.listeners):
            capabilities.definition_provider = True

    @rpc_method(name="textDocument/definition", param_type=DefinitionParams)
    async def _text_document_definition(
        self, text_document: TextDocumentIdentifier, position: Position, *args: Any, **kwargs: Any
    ) -> Optional[Union[Location, List[Location], List[LocationLink]]]:

        locations: List[Location] = []
        location_links: List[LocationLink] = []

        for result in await self.collect_definitions(self, self.parent.documents[text_document.uri], position):
            if isinstance(result, BaseException):
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
