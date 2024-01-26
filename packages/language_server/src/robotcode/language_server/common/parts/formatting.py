from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
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
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class FormattingProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    @event
    def format(
        sender,
        document: TextDocument,
        options: FormattingOptions,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]: ...

    @event
    def format_range(
        sender,
        document: TextDocument,
        range: Range,
        options: FormattingOptions,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.format):
            capabilities.document_formatting_provider = DocumentFormattingOptions(work_done_progress=True)
        if len(self.format_range):
            capabilities.document_range_formatting_provider = DocumentRangeFormattingOptions(work_done_progress=True)

    @rpc_method(name="textDocument/formatting", param_type=DocumentFormattingParams, threaded=True)
    def _text_document_formatting(
        self,
        params: DocumentFormattingParams,
        text_document: TextDocumentIdentifier,
        options: FormattingOptions,
        work_done_token: Optional[ProgressToken],
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[TextEdit]]:
        results: List[TextEdit] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.format(
            self,
            document,
            options,
            callback_filter=language_id_filter(document),
            **kwargs,
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if len(results) > 0:
            return results

        return None

    @rpc_method(name="textDocument/rangeFormatting", param_type=DocumentRangeFormattingParams, threaded=True)
    def _text_document_range_formatting(
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
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.format_range(
            self,
            document,
            range,
            options,
            callback_filter=language_id_filter(document),
            **kwargs,
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results += result

        if len(results) > 0:
            return results

        return None
