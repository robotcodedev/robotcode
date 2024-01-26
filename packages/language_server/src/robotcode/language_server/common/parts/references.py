from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    Location,
    Position,
    ReferenceContext,
    ReferenceOptions,
    ReferenceParams,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class ReferencesProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.references_provider = ReferenceOptions(work_done_progress=True)

    @event
    def collect(
        sender,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]: ...

    @rpc_method(name="textDocument/references", param_type=ReferenceParams, threaded=True)
    def _text_document_references(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        context: ReferenceContext,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[Location]]:
        self.parent.diagnostics.ensure_workspace_loaded()

        locations: List[Location] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(
            self,
            document,
            document.position_from_utf16(position),
            context,
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    locations.extend(result)

        if not locations:
            return None

        for location in locations:
            doc = self.parent.documents.get(location.uri)
            if doc is not None:
                location.range = doc.range_to_utf16(location.range)

        return locations
