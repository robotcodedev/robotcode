from concurrent.futures import CancelledError
from itertools import chain
from typing import TYPE_CHECKING, Any, Final, List, Optional, cast

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    Position,
    ServerCapabilities,
    SignatureHelp,
    SignatureHelpContext,
    SignatureHelpOptions,
    SignatureHelpParams,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import (
    RETRIGGER_CHARACTERS_ATTR,
    TRIGGER_CHARACTERS_ATTR,
    HasRetriggerCharacters,
    HasTriggerCharacters,
)

from .protocol_part import LanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class SignatureHelpProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    @event
    def collect(
        sender,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]: ...

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

            retrigger_chars = list(
                chain(
                    *[
                        cast(HasRetriggerCharacters, e).__retrigger_characters__
                        for e in self.collect
                        if hasattr(e, RETRIGGER_CHARACTERS_ATTR)
                    ]
                )
            )

            capabilities.signature_help_provider = SignatureHelpOptions(
                trigger_characters=trigger_chars if trigger_chars else None,
                retrigger_characters=retrigger_chars if retrigger_chars else None,
            )

    @rpc_method(name="textDocument/signatureHelp", param_type=SignatureHelpParams, threaded=True)
    def _text_document_signature_help(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[SignatureHelp]:
        results: List[SignatureHelp] = []

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in self.collect(
            self,
            document,
            document.position_from_utf16(position),
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

        if len(results) > 0 and results[-1].signatures:
            # TODO: can we combine signature help results?

            return results[-1]

        return None
