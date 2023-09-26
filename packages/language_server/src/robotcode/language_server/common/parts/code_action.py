from __future__ import annotations

from asyncio import CancelledError
from itertools import chain
from typing import TYPE_CHECKING, Any, Final, List, Optional, Union, cast

from robotcode.core.async_tools import async_tasking_event, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    CodeAction,
    CodeActionContext,
    CodeActionOptions,
    CodeActionParams,
    Command,
    Range,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import CODE_ACTION_KINDS_ATTR, HasCodeActionKinds, language_id_filter
from robotcode.language_server.common.has_extend_capabilities import HasExtendCapabilities
from robotcode.language_server.common.parts.protocol_part import LanguageServerProtocolPart
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class CodeActionProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

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
            code_action_kinds = list(
                chain(
                    *[
                        cast(HasCodeActionKinds, e).__code_action_kinds__
                        for e in self.collect
                        if hasattr(e, CODE_ACTION_KINDS_ATTR)
                    ]
                )
            )

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

        for c in context.diagnostics:
            c.range = document.range_from_utf16(c.range)
            if c.related_information is not None:
                for r in c.related_information:
                    r.location.range = document.range_from_utf16(r.location.range)

        for result in await self.collect(
            self,
            document,
            document.range_from_utf16(range),
            context,
            callback_filter=language_id_filter(document),
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.extend(result)

        if not results:
            return None

        return results

    @rpc_method(name="codeAction/resolve", param_type=CodeAction)
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
