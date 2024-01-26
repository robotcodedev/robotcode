from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Final, List, Optional

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    ErrorCodes,
    Position,
    PrepareRenameParams,
    PrepareRenameResult,
    PrepareRenameResultType1,
    Range,
    RenameOptions,
    RenameParams,
    ServerCapabilities,
    TextDocumentEdit,
    TextDocumentIdentifier,
    WorkspaceEdit,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import JsonRPCErrorException, rpc_method

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class CantRenameError(Exception):
    pass


class RenameProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.rename_provider = RenameOptions(
                prepare_provider=len(self.collect_prepare) > 0,
                work_done_progress=True,
            )

    @event
    def collect(
        sender,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]: ...

    @event
    def collect_prepare(sender, document: TextDocument, position: Position) -> Optional[PrepareRenameResult]: ...

    @rpc_method(name="textDocument/rename", param_type=RenameParams, threaded=True)
    def _text_document_rename(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        new_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[WorkspaceEdit]:
        edits: List[WorkspaceEdit] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(
            self,
            document,
            document.position_from_utf16(position),
            new_name,
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    edits.append(result)

        if not edits:
            return None

        for we in edits:
            check_current_task_canceled()

            if we.changes:
                for uri, changes in we.changes.items():
                    if changes:
                        doc = self.parent.documents.get(uri)
                        for change in changes:
                            if doc is not None:
                                change.range = doc.range_to_utf16(change.range)
            if we.document_changes:
                for doc_change in [v for v in we.document_changes if isinstance(v, TextDocumentEdit)]:
                    doc = self.parent.documents.get(doc_change.text_document.uri)
                    if doc is not None:
                        for edit in doc_change.edits:
                            edit.range = doc.range_to_utf16(edit.range)

        result = WorkspaceEdit()
        for we in edits:
            check_current_task_canceled()

            if we.changes:
                if result.changes is None:
                    result.changes = {}
                result.changes.update(we.changes)

            if we.document_changes:
                if result.document_changes is None:
                    result.document_changes = []
                result.document_changes.extend(we.document_changes)

            if we.change_annotations:
                if result.change_annotations is None:
                    result.change_annotations = {}
                result.change_annotations.update(we.change_annotations)

        return result

    @rpc_method(name="textDocument/prepareRename", param_type=PrepareRenameParams, threaded=True)
    def _text_document_prepare_rename(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[PrepareRenameResult]:
        results: List[PrepareRenameResult] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect_prepare(
            self,
            document,
            document.position_from_utf16(position),
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if isinstance(result, CantRenameError):
                    raise JsonRPCErrorException(ErrorCodes.INVALID_PARAMS, str(result))

                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if not results:
            return None

        result = results[-1]
        if isinstance(result, Range):
            result = document.range_to_utf16(result)
        elif isinstance(result, PrepareRenameResultType1):
            result.range = document.range_to_utf16(result.range)

        return result
