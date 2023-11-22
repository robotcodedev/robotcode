from __future__ import annotations

import asyncio
from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.async_tools import async_tasking_event, create_sub_task, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    CodeLens,
    CodeLensOptions,
    CodeLensParams,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import language_id_filter
from robotcode.language_server.common.has_extend_capabilities import HasExtendCapabilities
from robotcode.language_server.common.text_document import TextDocument

from .protocol_part import LanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class CodeLensProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self.refresh_task: Optional[asyncio.Task[Any]] = None

    @async_tasking_event
    async def collect(sender, document: TextDocument) -> Optional[List[CodeLens]]:  # NOSONAR
        ...

    @async_tasking_event
    async def resolve(sender, code_lens: CodeLens) -> Optional[CodeLens]:  # NOSONAR
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.code_lens_provider = CodeLensOptions(resolve_provider=True if len(self.resolve) > 0 else None)

    @rpc_method(name="textDocument/codeLens", param_type=CodeLensParams)
    @threaded()
    async def _text_document_code_lens(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> Optional[List[CodeLens]]:
        results: List[CodeLens] = []
        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(self, document, callback_filter=language_id_filter(document)):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.extend(result)

        if not results:
            return None

        for result in results:
            result.range = document.range_to_utf16(result.range)

        return results

    @rpc_method(name="codeLens/resolve", param_type=CodeLens)
    @threaded()
    async def _code_lens_resolve(self, params: CodeLens, *args: Any, **kwargs: Any) -> CodeLens:
        results: List[CodeLens] = []

        for result in await self.resolve(self, params):
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

    async def __do_refresh(self, now: bool = False) -> None:
        if not now:
            await asyncio.sleep(1)

        await self.__refresh()

    async def refresh(self, now: bool = False) -> None:
        if self.refresh_task is not None and not self.refresh_task.done():
            self.refresh_task.get_loop().call_soon_threadsafe(self.refresh_task.cancel)

        self.refresh_task = create_sub_task(self.__do_refresh(now), loop=self.parent.diagnostics.diagnostics_loop)

    async def __refresh(self) -> None:
        if not (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.workspace is not None
            and self.parent.client_capabilities.workspace.code_lens is not None
            and self.parent.client_capabilities.workspace.code_lens.refresh_support
        ):
            return

        await self.parent.send_request_async("workspace/codeLens/refresh")
