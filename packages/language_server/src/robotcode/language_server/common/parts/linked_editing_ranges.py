from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    LinkedEditingRangeOptions,
    LinkedEditingRangeParams,
    LinkedEditingRanges,
    Position,
    Range,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class LinkedEditingRangeProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.linked_editing_range_provider = LinkedEditingRangeOptions(work_done_progress=True)

    @event
    def collect(sender, document: TextDocument, position: Position) -> Optional[LinkedEditingRanges]: ...

    @rpc_method(name="textDocument/linkedEditingRange", param_type=LinkedEditingRangeParams, threaded=True)
    def _text_document_linked_editing_range(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[LinkedEditingRanges]:
        linked_ranges: List[Range] = []
        word_pattern: Optional[str] = None

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
                    linked_ranges.extend(result.ranges)
                    if result.word_pattern is not None:
                        word_pattern = result.word_pattern

        return LinkedEditingRanges([document.range_to_utf16(r) for r in linked_ranges], word_pattern)
