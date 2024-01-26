from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    Hover,
    HoverOptions,
    HoverParams,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class HoverProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    @event
    def collect(sender, document: TextDocument, position: Position) -> Optional[Hover]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.hover_provider = HoverOptions(work_done_progress=True)

    @rpc_method(name="textDocument/hover", param_type=HoverParams, threaded=True)
    def _text_document_hover(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[Hover]:
        results: List[Hover] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(
            self,
            document,
            document.position_from_utf16(position),
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        for result in results:
            if result.range is not None:
                result.range = document.range_to_utf16(result.range)

        if len(results) > 0 and results[-1].contents:
            # TODO: how can we combine hover results?

            return results[-1]

        return None
