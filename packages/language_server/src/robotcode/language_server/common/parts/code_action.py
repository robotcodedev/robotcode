from concurrent.futures import CancelledError
from itertools import chain
from typing import TYPE_CHECKING, Any, Final, List, Optional, Union, cast

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
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
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import CODE_ACTION_KINDS_ATTR, HasCodeActionKinds
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class CodeActionProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    @event
    def collect(
        sender,
        document: TextDocument,
        range: Range,
        context: CodeActionContext,
    ) -> Optional[List[Union[Command, CodeAction]]]: ...

    @event
    def resolve(sender, code_action: CodeAction) -> Optional[CodeAction]: ...

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

    @rpc_method(name="textDocument/codeAction", param_type=CodeActionParams, threaded=True)
    def _text_document_code_action(
        self,
        text_document: TextDocumentIdentifier,
        range: Range,
        context: CodeActionContext,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[Union[Command, CodeAction]]]:
        results: List[Union[Command, CodeAction]] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for c in context.diagnostics:
            c.range = document.range_from_utf16(c.range)
            if c.related_information is not None:
                for r in c.related_information:
                    r.location.range = document.range_from_utf16(r.location.range)

        for result in self.collect(
            self,
            document,
            document.range_from_utf16(range),
            context,
            callback_filter=language_id_filter(document),
        ):
            check_current_task_canceled()

            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.extend(result)

        if not results:
            return None

        return results

    @rpc_method(name="codeAction/resolve", param_type=CodeAction, threaded=True)
    def _text_document_code_action_resolve(self, params: CodeAction, *args: Any, **kwargs: Any) -> CodeAction:
        results: List[CodeAction] = []

        for result in self.resolve(self, params):
            check_current_task_canceled()

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
