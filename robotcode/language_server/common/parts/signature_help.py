from __future__ import annotations

from asyncio import CancelledError
from itertools import chain
from typing import TYPE_CHECKING, Any, List, Optional, cast

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import (
    HasRetriggerCharacters,
    HasTriggerCharacters,
    language_id_filter,
)
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    Position,
    ServerCapabilities,
    SignatureHelp,
    SignatureHelpContext,
    SignatureHelpOptions,
    SignatureHelpParams,
    TextDocumentIdentifier,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class SignatureHelpProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def collect(
        sender, document: TextDocument, position: Position, context: Optional[SignatureHelpContext] = None  # NOSONAR
    ) -> Optional[SignatureHelp]:
        ...

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect):
            trigger_chars = [
                k
                for k in chain(
                    *[
                        cast(HasTriggerCharacters, e).__trigger_characters__
                        for e in self.collect
                        if isinstance(e, HasTriggerCharacters)
                    ]
                )
            ]

            retrigger_chars = [
                k
                for k in chain(
                    *[
                        cast(HasRetriggerCharacters, e).__retrigger_characters__
                        for e in self.collect
                        if isinstance(e, HasRetriggerCharacters)
                    ]
                )
            ]

            capabilities.signature_help_provider = SignatureHelpOptions(
                trigger_characters=trigger_chars if trigger_chars else None,
                retrigger_characters=retrigger_chars if retrigger_chars else None,
            )

    @rpc_method(name="textDocument/signatureHelp", param_type=SignatureHelpParams)
    @threaded()
    async def _text_document_signature_help(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[SignatureHelp]:

        results: List[SignatureHelp] = []

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

        if len(results) > 0 and results[-1].signatures:
            # TODO: can we combine signature help results?

            return results[-1]

        return None
