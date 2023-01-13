from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from ....jsonrpc2.protocol import JsonRPCErrorException, rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    ErrorCodes,
    Position,
    PrepareRenameParams,
    PrepareRenameResult,
    RenameOptions,
    RenameParams,
    ServerCapabilities,
    TextDocumentIdentifier,
    WorkspaceEdit,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class CantRenameException(Exception):
    pass


class RenameProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            capabilities.rename_provider = RenameOptions(
                prepare_provider=len(self.collect_prepare) > 0, work_done_progress=True
            )

    @async_tasking_event
    async def collect(
        sender, document: TextDocument, position: Position, new_name: str  # NOSONAR
    ) -> Optional[WorkspaceEdit]:
        ...

    @async_tasking_event
    async def collect_prepare(
        sender, document: TextDocument, position: Position  # NOSONAR
    ) -> Optional[PrepareRenameResult]:
        ...

    @rpc_method(name="textDocument/rename", param_type=RenameParams)
    @threaded()
    async def _text_document_rename(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        new_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[WorkspaceEdit]:

        edits: List[WorkspaceEdit] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(
            self, document, position, new_name, callback_filter=language_id_filter(document)
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    edits.append(result)

        if len(edits) == 0:
            return None

        result = WorkspaceEdit()
        for we in edits:
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

    @rpc_method(name="textDocument/prepareRename", param_type=PrepareRenameParams)
    @threaded()
    async def _text_document_prepare_rename(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[PrepareRenameResult]:

        results: List[PrepareRenameResult] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect_prepare(
            self, document, position, callback_filter=language_id_filter(document)
        ):
            if isinstance(result, BaseException):
                if isinstance(result, CantRenameException):
                    raise JsonRPCErrorException(ErrorCodes.INVALID_PARAMS, str(result))

                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if len(results) == 0:
            return None

        return results[-1]
