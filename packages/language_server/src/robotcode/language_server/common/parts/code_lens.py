import threading
from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    CodeLens,
    CodeLensOptions,
    CodeLensParams,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method

from .protocol_part import LanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class CodeLensProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.refresh_timer_lock = threading.RLock()
        self.refresh_timer: Optional[threading.Timer] = None

    @event
    def collect(sender, document: TextDocument) -> Optional[List[CodeLens]]: ...

    @event
    def resolve(sender, code_lens: CodeLens) -> Optional[CodeLens]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.code_lens_provider = CodeLensOptions(resolve_provider=True if len(self.resolve) > 0 else None)

    @rpc_method(name="textDocument/codeLens", param_type=CodeLensParams, threaded=True)
    def _text_document_code_lens(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> Optional[List[CodeLens]]:
        results: List[CodeLens] = []
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(self, document, callback_filter=language_id_filter(document)):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.extend(result)

        if not results:
            return None

        for r in results:
            r.range = document.range_to_utf16(r.range)

        return results

    @rpc_method(name="codeLens/resolve", param_type=CodeLens, threaded=True)
    def _code_lens_resolve(self, params: CodeLens, *args: Any, **kwargs: Any) -> CodeLens:
        results: List[CodeLens] = []

        for result in self.resolve(self, params):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if len(results) > 1:
            self._logger.warning("More then one resolve result collected.")
            return results[-1]

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
            and self.parent.client_capabilities.workspace.code_lens is not None
            and self.parent.client_capabilities.workspace.code_lens.refresh_support
        ):
            self.parent.send_request("workspace/codeLens/refresh")
