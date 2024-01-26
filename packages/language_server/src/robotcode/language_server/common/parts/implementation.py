from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional, Union

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    ImplementationParams,
    Location,
    LocationLink,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class ImplementationProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.link_support = False

    @event
    def collect(
        sender,
        document: TextDocument,
        position: Position,
    ) -> Union[Location, List[Location], List[LocationLink], None]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.text_document is not None
            and self.parent.client_capabilities.text_document.implementation
        ):
            self.link_support = self.parent.client_capabilities.text_document.implementation.link_support or False

        if len(self.collect):
            capabilities.implementation_provider = True

    @rpc_method(name="textDocument/implementation", param_type=ImplementationParams, threaded=True)
    def _text_document_implementation(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[Union[Location, List[Location], List[LocationLink]]]:
        locations: List[Location] = []
        location_links: List[LocationLink] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(
            self,
            document,
            position,
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

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

        if locations:
            for location in locations:
                doc = self.parent.documents.get(location.uri)
                if doc is not None:
                    location.range = doc.range_to_utf16(location.range)

        if location_links:
            for location_link in location_links:
                doc = self.parent.documents.get(location_link.target_uri)
                if doc is not None:
                    location_link.target_range = doc.range_to_utf16(location_link.target_range)
                    location_link.target_selection_range = doc.range_to_utf16(location_link.target_selection_range)
                if location_link.origin_selection_range is not None:
                    location_link.origin_selection_range = document.range_to_utf16(location_link.origin_selection_range)

        if len(locations) > 0 and len(location_links) == 0:
            if len(locations) == 1:
                return locations[0]

            return locations

        if len(locations) > 0 and len(location_links) > 0:
            self._logger.warning("can't mix Locations and LocationLinks")

        if self.link_support:
            return location_links

        self._logger.warning("client has no link_support capability, convert LocationLinks to Location")

        return [Location(uri=e.target_uri, range=e.target_range) for e in location_links]
