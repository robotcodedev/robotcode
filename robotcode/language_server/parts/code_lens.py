from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from ...jsonrpc2.protocol import rpc_method
from ...utils.async_event import async_tasking_event
from ...utils.logging import LoggingDescriptor
from ..has_extend_capabilities import HasExtendCapabilities
from ..language import HasLanguageId
from ..text_document import TextDocument
from ..types import (
    CodeLens,
    CodeLensOptions,
    CodeLensParams,
    ServerCapabilities,
    TextDocumentIdentifier,
)

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class CodeLensProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def collect(sender, document: TextDocument) -> Optional[List[CodeLens]]:
        ...

    @async_tasking_event
    async def resolve(sender, code_lens: CodeLens) -> Optional[CodeLens]:
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.code_lens_provider = CodeLensOptions(resolve_provider=True if len(self.resolve) > 0 else None)

    @rpc_method(name="textDocument/codeLens", param_type=CodeLensParams)
    async def _text_document_code_lens(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> Optional[List[CodeLens]]:

        results: List[CodeLens] = []
        document = self.parent.documents[text_document.uri]
        for result in await self.collect(
            self,
            document,
            callback_filter=lambda c: not isinstance(c, HasLanguageId) or c.__language_id__ == document.language_id,
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
                self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.extend(result)

        if len(results) > 0:
            return results

        return None

    @rpc_method(name="codeLens/resolve", param_type=CodeLens)
    async def _code_lens_resolve(self, params: CodeLens, *args: Any, **kwargs: Any) -> CodeLens:

        results: List[CodeLens] = []

        for result in await self.resolve(self, params):
            if isinstance(result, BaseException):
                self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if len(results) > 0:
            self._logger.warning("More then one resolve result collected.")
            return results[-1]

        return params

    async def refresh(self) -> None:
        if not (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.workspace is not None
            and self.parent.client_capabilities.workspace.code_lens is not None
            and self.parent.client_capabilities.workspace.code_lens.refresh_support
        ):
            pass

        await self.parent.send_request("workspace/codeLens/refresh")
