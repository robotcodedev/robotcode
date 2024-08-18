import dataclasses
from concurrent.futures import CancelledError
from itertools import chain
from typing import TYPE_CHECKING, Any, Final, List, Optional, Union, cast

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    CompletionContext,
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionOptionsCompletionItemType,
    CompletionParams,
    CompletionTriggerKind,
    InsertReplaceEdit,
    Position,
    ServerCapabilities,
    TextDocumentIdentifier,
    TextEdit,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import (
    ALL_COMMIT_CHARACTERS_ATTR,
    TRIGGER_CHARACTERS_ATTR,
    HasAllCommitCharacters,
    HasTriggerCharacters,
)
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class CompletionProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.resolve_support = False

    @event
    def collect(
        sender,
        document: TextDocument,
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]: ...

    @event
    def resolve(sender, completion_item: CompletionItem) -> Optional[CompletionItem]: ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            trigger_chars = list(
                chain(
                    *[
                        cast(HasTriggerCharacters, e).__trigger_characters__
                        for e in self.collect
                        if hasattr(e, TRIGGER_CHARACTERS_ATTR)
                    ]
                )
            )

            commit_chars = list(
                chain(
                    *[
                        cast(HasAllCommitCharacters, e).__all_commit_characters__
                        for e in self.collect
                        if hasattr(e, ALL_COMMIT_CHARACTERS_ATTR)
                    ]
                )
            )
            if (
                self.parent.client_capabilities is not None
                and self.parent.client_capabilities.text_document is not None
                and self.parent.client_capabilities.text_document.completion is not None
                and self.parent.client_capabilities.text_document.completion.completion_item is not None
                and self.parent.client_capabilities.text_document.completion.completion_item.resolve_support is not None
                and self.parent.client_capabilities.text_document.completion.completion_item.resolve_support.properties
            ):
                self.resolve_support = True

            capabilities.completion_provider = CompletionOptions(
                trigger_characters=trigger_chars if trigger_chars else None,
                all_commit_characters=commit_chars if commit_chars else None,
                resolve_provider=len(self.resolve) > 0,
                work_done_progress=True,
                completion_item=CompletionOptionsCompletionItemType(label_details_support=True),
            )

    @rpc_method(name="textDocument/completion", param_type=CompletionParams, threaded=True)
    def _text_document_completion(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        context: Optional[CompletionContext],
        *args: Any,
        **kwargs: Any,
    ) -> Union[List[CompletionItem], CompletionList, None]:
        results: List[Union[List[CompletionItem], CompletionList]] = []

        if context is not None and context.trigger_kind == CompletionTriggerKind.TRIGGER_CHARACTER:
            check_current_task_canceled(0.25)

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        p = document.position_from_utf16(position)

        for result in self.collect(
            self,
            document,
            p,
            context,
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if not results:
            return None

        for result in results:
            check_current_task_canceled()

            if isinstance(result, CompletionList):
                for item in result.items:
                    if item.text_edit is not None:
                        self.update_completion_item_to_utf16(document, item)

            elif isinstance(result, list):
                for item in result:
                    if item.text_edit is not None:
                        self.update_completion_item_to_utf16(document, item)

        if any(e for e in results if isinstance(e, CompletionList)):
            result = CompletionList(
                is_incomplete=any(e for e in results if isinstance(e, CompletionList) and e.is_incomplete),
                items=list(chain(*[r.items if isinstance(r, CompletionList) else r for r in results])),
            )
            if len(result.items) == 0:
                return None

            if self.resolve_support:
                return result

            return dataclasses.replace(result, items=[self._completion_item_resolve(e) for e in result.items])

        result = list(chain(*[k for k in results if isinstance(k, list)]))
        if not result:
            return None

        if self.resolve_support:
            return result

        return [self._completion_item_resolve(e) for e in result]

    def update_completion_item_to_utf16(self, document: TextDocument, item: CompletionItem) -> None:
        if isinstance(item.text_edit, TextEdit):
            item.text_edit.range = document.range_to_utf16(item.text_edit.range)
        elif isinstance(item.text_edit, InsertReplaceEdit):
            item.text_edit.insert = document.range_to_utf16(item.text_edit.insert)
            item.text_edit.replace = document.range_to_utf16(item.text_edit.replace)

    @rpc_method(name="completionItem/resolve", param_type=CompletionItem, threaded=True)
    def _completion_item_resolve(self, params: CompletionItem, *args: Any, **kwargs: Any) -> CompletionItem:
        results: List[CompletionItem] = []

        for result in self.resolve(self, params):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        if not results:
            return params

        if len(results) > 1:
            self._logger.warning("More then one resolve result. Use the last one.")
        return results[-1]
