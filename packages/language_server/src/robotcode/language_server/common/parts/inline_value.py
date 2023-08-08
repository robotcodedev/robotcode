from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.async_tools import async_tasking_event, threaded
from robotcode.core.logging import LoggingDescriptor
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
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import (
    LANGUAGE_ID_ATTR,
    language_id_filter,
)
from robotcode.language_server.common.has_extend_capabilities import (
    HasExtendCapabilities,
)
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol  # pragma: no cover


class InlineValueProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def collect(
        sender,
        document: TextDocument,
        range: Range,
        context: InlineValueContext,  # pragma: no cover, NOSONAR
    ) -> Optional[List[InlineValue]]:
        ...

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

    @rpc_method(name="textDocument/inlineValue", param_type=InlineValueParams)
    @threaded()
    async def _text_document_inline_value(
        self,
        text_document: TextDocumentIdentifier,
        range: Range,
        context: InlineValueContext,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[InlineValue]]:
        results: List[InlineValue] = []
        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(
            self, document, document.range_from_utf16(range), context, callback_filter=language_id_filter(document)
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if not results:
            return None

        for result in results:
            result.range = document.range_to_utf16(result.range)

        return results

    async def refresh(self) -> None:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.inline_value
            and self.parent.client_capabilities.workspace.inline_value.refresh_support
        ):
            await self.parent.send_request_async("workspace/inlineValue/refresh")
