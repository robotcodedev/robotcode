from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    DocumentFormattingOptions,
    DocumentFormattingParams,
    DocumentRangeFormattingOptions,
    DocumentRangeFormattingParams,
    FormattingOptions,
    ProgressToken,
    Range,
    ServerCapabilities,
    TextDocumentIdentifier,
    TextEdit,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class FormattingProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def format(
        sender, document: TextDocument, options: FormattingOptions, **further_options: Any  # NOSONAR
    ) -> Optional[List[TextEdit]]:
        ...

    @async_tasking_event
    async def format_range(
        sender, document: TextDocument, range: Range, options: FormattingOptions, **further_options: Any  # NOSONAR
    ) -> Optional[List[TextEdit]]:
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.format):
            capabilities.document_formatting_provider = DocumentFormattingOptions(work_done_progress=True)
        if len(self.format_range):
            capabilities.document_range_formatting_provider = DocumentRangeFormattingOptions(work_done_progress=True)

    @rpc_method(name="textDocument/formatting", param_type=DocumentFormattingParams)
    @threaded()
    async def _text_document_formatting(
        self,
        params: DocumentFormattingParams,
        text_document: TextDocumentIdentifier,
        options: FormattingOptions,
        work_done_token: Optional[ProgressToken],
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[TextEdit]]:

        results: List[TextEdit] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.format(
            self,
            document,
            options,
            callback_filter=language_id_filter(document),
            **kwargs,
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if len(results) > 0:
            return results

        return None

    @rpc_method(name="textDocument/rangeFormatting", param_type=DocumentRangeFormattingParams)
    @threaded()
    async def _text_document_range_formatting(
        self,
        params: DocumentFormattingParams,
        text_document: TextDocumentIdentifier,
        range: Range,
        options: FormattingOptions,
        work_done_token: Optional[ProgressToken],
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[TextEdit]]:

        results: List[TextEdit] = []
        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.format_range(
            self,
            document,
            range,
            options,
            callback_filter=language_id_filter(document),
            **kwargs,
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if len(results) > 0:
            return results

        return None
