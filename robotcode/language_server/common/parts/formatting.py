from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_event import async_tasking_event
from ....utils.logging import LoggingDescriptor
from ..has_extend_capabilities import HasExtendCapabilities
from ..language import HasLanguageId
from ..text_document import TextDocument
from ..types import (
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

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class FormattingProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def format(
        sender, document: TextDocument, options: FormattingOptions, **further_options: Any
    ) -> Optional[List[TextEdit]]:
        ...

    @async_tasking_event
    async def format_range(
        sender, document: TextDocument, range: Range, options: FormattingOptions, **further_options: Any
    ) -> Optional[List[TextEdit]]:
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.format):
            capabilities.document_formatting_provider = DocumentFormattingOptions(work_done_progress=True)
        if len(self.format_range):
            capabilities.document_range_formatting_provider = DocumentRangeFormattingOptions(work_done_progress=True)

    @rpc_method(name="textDocument/formatting", param_type=DocumentFormattingParams)
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
        document = self.parent.documents[text_document.uri]
        for result in await self.format(
            self,
            document,
            options,
            callback_filter=lambda c: not isinstance(c, HasLanguageId) or c.__language_id__ == document.language_id,
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
        document = self.parent.documents[text_document.uri]
        for result in await self.format_range(
            self,
            document,
            range,
            options,
            callback_filter=lambda c: not isinstance(c, HasLanguageId) or c.__language_id__ == document.language_id,
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
