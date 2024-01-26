from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    Position,
    SelectionRange,
    SelectionRangeOptions,
    SelectionRangeParams,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class SelectionRangeProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.selection_range_provider = SelectionRangeOptions(work_done_progress=True)

    @event
    def collect(sender, document: TextDocument, positions: List[Position]) -> Optional[List[SelectionRange]]: ...

    @rpc_method(name="textDocument/selectionRange", param_type=SelectionRangeParams, threaded=True)
    def _text_document_selection_range(
        self,
        text_document: TextDocumentIdentifier,
        positions: List[Position],
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[SelectionRange]]:
        results: List[SelectionRange] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(
            self,
            document,
            [document.position_from_utf16(p) for p in positions],
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.extend(result)

        if not results:
            return None

        def traverse(selection_range: SelectionRange, doc: TextDocument) -> None:
            selection_range.range = doc.range_to_utf16(selection_range.range)
            if selection_range.parent is not None:
                traverse(selection_range.parent, doc)

        for r in results:
            traverse(r, document)

        return results
