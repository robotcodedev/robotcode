import threading
from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import (
    LANGUAGE_ID_ATTR,
    language_id_filter,
)
from robotcode.core.lsp.types import (
    DocumentSelector,
    InlineValue,
    InlineValueContext,
    InlineValueParams,
    InlineValueRegistrationOptions,
    Range,
    ServerCapabilities,
    TextDocumentFilterType1,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import (
        LanguageServerProtocol,
    )


class InlineValueProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.refresh_timer_lock = threading.RLock()
        self.refresh_timer: Optional[threading.Timer] = None

    @event
    def collect(
        sender,
        document: TextDocument,
        range: Range,
        context: InlineValueContext,  # pragma: no cover, NOSONAR
    ) -> Optional[List[InlineValue]]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            document_filters: DocumentSelector = []
            for e in self.collect:
                if hasattr(e, LANGUAGE_ID_ATTR):
                    for lang_id in getattr(e, LANGUAGE_ID_ATTR):
                        document_filters.append(TextDocumentFilterType1(language=lang_id))
            capabilities.inline_value_provider = InlineValueRegistrationOptions(
                work_done_progress=True,
                document_selector=document_filters if document_filters else None,
            )

    @rpc_method(name="textDocument/inlineValue", param_type=InlineValueParams, threaded=True)
    def _text_document_inline_value(
        self,
        text_document: TextDocumentIdentifier,
        range: Range,
        context: InlineValueContext,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[InlineValue]]:
        results: List[InlineValue] = []
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(
            self,
            document,
            document.range_from_utf16(range),
            context,
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if not results:
            return None

        for r in results:
            r.range = document.range_to_utf16(r.range)

        return results

    def refresh(self, now: bool = False) -> None:
        with self.refresh_timer_lock:
            if self.refresh_timer is not None:
                self.refresh_timer.cancel()
                self.refresh_timer = None

            if not now:
                self.refresh_timer = threading.Timer(1, self._refresh)
                self.refresh_timer.start()
                return

        self._refresh()

    def _refresh(self) -> None:
        with self.refresh_timer_lock:
            self.refresh_timer = None

        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.inline_value
            and self.parent.client_capabilities.workspace.inline_value.refresh_support
        ):
            self.parent.send_request("workspace/inlineValue/refresh")
