from __future__ import annotations

from asyncio import CancelledError
from itertools import chain
from typing import TYPE_CHECKING, Any, Final, List, Optional, Union, cast

from robotcode.core.async_tools import async_tasking_event, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import HasAllCommitCharacters, HasTriggerCharacters, language_id_filter
from robotcode.language_server.common.has_extend_capabilities import HasExtendCapabilities
from robotcode.language_server.common.lsp_types import (
    CompletionContext,
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from robotcode.language_server.common.parts.protocol_part import LanguageServerProtocolPart
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class CompletionProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def collect(
        sender, document: TextDocument, position: Position, context: Optional[CompletionContext]  # NOSONAR
    ) -> Union[List[CompletionItem], CompletionList, None]:
        ...

    @async_tasking_event
    async def resolve(sender, completion_item: CompletionItem) -> Optional[CompletionItem]:  # NOSONAR
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            trigger_chars = list(
                chain(
                    *[
                        cast(HasTriggerCharacters, e).__trigger_characters__
                        for e in self.collect
                        if isinstance(e, HasTriggerCharacters)
                    ]
                )
            )

            commit_chars = list(
                chain(
                    *[
                        cast(HasAllCommitCharacters, e).__all_commit_characters__
                        for e in self.collect
                        if isinstance(e, HasAllCommitCharacters)
                    ]
                )
            )
            capabilities.completion_provider = CompletionOptions(
                trigger_characters=trigger_chars if trigger_chars else None,
                all_commit_characters=commit_chars if commit_chars else None,
                resolve_provider=len(self.resolve) > 0,
                work_done_progress=True,
            )

    @rpc_method(name="textDocument/completion", param_type=CompletionParams)
    @threaded()
    async def _text_document_completion(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        context: Optional[CompletionContext],
        *args: Any,
        **kwargs: Any,
    ) -> Union[List[CompletionItem], CompletionList, None]:
        results: List[Union[List[CompletionItem], CompletionList]] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect(
            self,
            document,
            position,
            context,
            callback_filter=language_id_filter(document),
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if len(results) > 0:
            if any(e for e in results if isinstance(e, CompletionList)):
                result = CompletionList(
                    is_incomplete=any(e for e in results if isinstance(e, CompletionList) and e.is_incomplete),
                    items=list(chain(*[r.items if isinstance(r, CompletionList) else r for r in results])),
                )
                if len(result.items) == 0:
                    return None
                return result

            result = list(chain(*[k for k in results if isinstance(k, list)]))
            if len(result) == 0:
                return None

            return result

        return None

    @rpc_method(name="completionItem/resolve", param_type=CompletionItem)
    @threaded()
    async def _completion_item_resolve(
        self,
        params: CompletionItem,
        *args: Any,
        **kwargs: Any,
    ) -> CompletionItem:
        results: List[CompletionItem] = []

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
