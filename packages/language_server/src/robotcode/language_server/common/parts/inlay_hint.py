import threading
from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    InlayHint,
    InlayHintOptions,
    InlayHintParams,
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


class InlayHintProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.refresh_timer_lock = threading.RLock()
        self.refresh_timer: Optional[threading.Timer] = None

    @event
    def collect(sender, document: TextDocument, range: Range) -> Optional[List[InlayHint]]: ...

    @event
    def resolve(sender, hint: InlayHint) -> Optional[InlayHint]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            if len(self.resolve):
                capabilities.inlay_hint_provider = InlayHintOptions(resolve_provider=bool(len(self.resolve)))
            else:
                capabilities.inlay_hint_provider = InlayHintOptions()

    @rpc_method(name="textDocument/inlayHint", param_type=InlayHintParams, threaded=True)
    def _text_document_inlay_hint(
        self,
        text_document: TextDocumentIdentifier,
        range: Range,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[InlayHint]]:
        results: List[InlayHint] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(
            self,
            document,
            document.range_from_utf16(range),
            callback_filter=language_id_filter(document),
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.extend(result)

        if results:
            for r in results:
                r.position = document.position_to_utf16(r.position)
                # TODO: resolve

            return results

        return None

    @rpc_method(name="inlayHint/resolve", param_type=InlayHint, threaded=True)
    def _inlay_hint_resolve(self, params: InlayHint, *args: Any, **kwargs: Any) -> Optional[InlayHint]:
        for result in self.resolve(self, params):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if isinstance(result, InlayHint):
                    return result

        return params

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
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.workspace is not None
            and self.parent.client_capabilities.workspace.inlay_hint is not None
            and self.parent.client_capabilities.workspace.inlay_hint.refresh_support
        ):
            self.parent.send_request("workspace/inlayHint/refresh")
