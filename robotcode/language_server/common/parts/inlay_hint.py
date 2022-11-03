from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    InlayHint,
    InlayHintOptions,
    InlayHintParams,
    Range,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class InlayHintProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def collect(sender, document: TextDocument, range: Range) -> Optional[List[InlayHint]]:  # NOSONAR
        ...

    @async_tasking_event
    async def resolve(sender, hint: InlayHint) -> Optional[InlayHint]:  # NOSONAR
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            if len(self.resolve):
                capabilities.inlay_hint_provider = InlayHintOptions(resolve_provider=bool(len(self.resolve)))
            else:
                capabilities.inlay_hint_provider = InlayHintOptions()

    @rpc_method(name="textDocument/inlayHint", param_type=InlayHintParams)
    @threaded()
    async def _text_document_inlay_hint(
        self,
        text_document: TextDocumentIdentifier,
        range: Range,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[InlayHint]]:

        results: List[InlayHint] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(
            self,
            document,
            range,
            callback_filter=language_id_filter(document),
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.extend(result)

        if len(results) > 0:
            return results

        return None

    @rpc_method(name="inlayHint/resolve", param_type=InlayHint)
    @threaded()
    async def _inlay_hint_resolve(
        self,
        params: InlayHint,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[InlayHint]:

        for result in await self.resolve(self, params):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if isinstance(result, InlayHint):
                    return result

        return params

    async def refresh(self) -> None:
        if (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.workspace is not None
            and self.parent.client_capabilities.workspace.inlay_hint is not None
            and self.parent.client_capabilities.workspace.inlay_hint.refresh_support
        ):
            await self.parent.send_request_async("workspace/inlayHint/refresh")
