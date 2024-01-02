from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import threaded
from robotcode.core.event import event
from robotcode.core.lsp.types import (
    InlayHint,
    InlayHintOptions,
    InlayHintParams,
    Range,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import language_id_filter
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class InlayHintProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    @event
    def collect(sender, document: TextDocument, range: Range) -> Optional[List[InlayHint]]:  # NOSONAR
        ...

    @event
    def resolve(sender, hint: InlayHint) -> Optional[InlayHint]:  # NOSONAR
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            if len(self.resolve):
                capabilities.inlay_hint_provider = InlayHintOptions(resolve_provider=bool(len(self.resolve)))
            else:
                capabilities.inlay_hint_provider = InlayHintOptions()

    @rpc_method(name="textDocument/inlayHint", param_type=InlayHintParams)
    @threaded
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

    @rpc_method(name="inlayHint/resolve", param_type=InlayHint)
    @threaded
    def _inlay_hint_resolve(
        self,
        params: InlayHint,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[InlayHint]:
        for result in self.resolve(self, params):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if isinstance(result, InlayHint):
                    return result

        return params

    def refresh(self) -> None:
        if (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.workspace is not None
            and self.parent.client_capabilities.workspace.inlay_hint is not None
            and self.parent.client_capabilities.workspace.inlay_hint.refresh_support
        ):
            self.parent.send_request("workspace/inlayHint/refresh").result()
