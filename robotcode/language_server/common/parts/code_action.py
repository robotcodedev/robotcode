from __future__ import annotations

from asyncio import CancelledError
from itertools import chain
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import HasCodeActionKinds, language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    CodeAction,
    CodeActionContext,
    CodeActionOptions,
    CodeActionParams,
    Command,
    Range,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class CodeActionProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def collect(
        sender, document: TextDocument, range: Range, context: CodeActionContext  # NOSONAR
    ) -> Optional[List[Union[Command, CodeAction]]]:
        ...

    @async_tasking_event
    async def resolve(sender, code_action: CodeAction) -> Optional[CodeAction]:  # NOSONAR
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            code_action_kinds = [
                k
                for k in chain(
                    *[
                        cast(HasCodeActionKinds, e).__code_action_kinds__
                        for e in self.collect
                        if isinstance(e, HasCodeActionKinds)
                    ]
                )
            ]

            capabilities.code_action_provider = CodeActionOptions(
                code_action_kinds=code_action_kinds if code_action_kinds else None,
                resolve_provider=len(self.resolve) > 0,
            )

    @rpc_method(name="textDocument/codeAction", param_type=CodeActionParams)
    @threaded()
    async def _text_document_code_action(
        self,
        text_document: TextDocumentIdentifier,
        range: Range,
        context: CodeActionContext,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[Union[Command, CodeAction]]]:

        results: List[Union[Command, CodeAction]] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(
            self,
            document,
            range,
            context,
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

    @rpc_method(name="textDocument/codeAction/resolve", param_type=CodeAction)
    @threaded()
    async def _text_document_code_action_resolve(
        self,
        params: CodeAction,
        *args: Any,
        **kwargs: Any,
    ) -> CodeAction:

        results: List[CodeAction] = []

        for result in await self.resolve(self, params):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if len(results) > 0:
            if len(results) > 1:
                self._logger.warning("More then one resolve result. Use the last one.")

            return results[-1]

        return params
