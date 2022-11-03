from __future__ import annotations

from asyncio import CancelledError
from enum import Enum
from typing import TYPE_CHECKING, Any, List, Union

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import async_tasking_event, threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    Range,
    SemanticTokenModifiers,
    SemanticTokens,
    SemanticTokensDelta,
    SemanticTokensDeltaParams,
    SemanticTokensDeltaPartialResult,
    SemanticTokensLegend,
    SemanticTokensOptions,
    SemanticTokensOptionsFull,
    SemanticTokensParams,
    SemanticTokensPartialResult,
    SemanticTokensRangeParams,
    SemanticTokenTypes,
    ServerCapabilities,
    TextDocumentIdentifier,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart


class SemanticTokensProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

    @async_tasking_event
    async def collect_full(
        sender, document: TextDocument, **kwargs: Any  # NOSONAR
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        ...

    @async_tasking_event
    async def collect_full_delta(
        sender, document: TextDocument, previous_result_id: str, **kwargs: Any  # NOSONAR
    ) -> Union[SemanticTokens, SemanticTokensDelta, SemanticTokensDeltaPartialResult, None]:
        ...

    @async_tasking_event
    async def collect_range(
        sender, document: TextDocument, range: Range, **kwargs: Any  # NOSONAR
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        ...

    token_types: List[Enum] = [e for e in SemanticTokenTypes]
    token_modifiers: List[Enum] = [e for e in SemanticTokenModifiers]

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if len(self.collect_full) or len(self.collect_range):
            capabilities.semantic_tokens_provider = SemanticTokensOptions(
                legend=SemanticTokensLegend(
                    token_types=[e.value for e in self.token_types],
                    token_modifiers=[e.value for e in self.token_modifiers],
                ),
                full=SemanticTokensOptionsFull(delta=True if len(self.collect_full_delta) else None)
                if len(self.collect_full) and len(self.collect_full_delta)
                else True
                if len(self.collect_full)
                else None,
                range=True if len(self.collect_range) else None,
            )

    @rpc_method(name="textDocument/semanticTokens/full", param_type=SemanticTokensParams)
    @threaded()
    async def _text_document_semantic_tokens_full(
        self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:

        results: List[Union[SemanticTokens, SemanticTokensPartialResult]] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect_full(
            self,
            document,
            callback_filter=language_id_filter(document),
            **kwargs,
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        # only the last is returned
        if len(results) > 0:
            return results[-1]

        return None

    @rpc_method(name="textDocument/semanticTokens/full/delta", param_type=SemanticTokensDeltaParams)
    @threaded()
    async def _text_document_semantic_tokens_full_delta(
        self, text_document: TextDocumentIdentifier, previous_result_id: str, *args: Any, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensDelta, SemanticTokensDeltaPartialResult, None]:

        results: List[Union[SemanticTokens, SemanticTokensDelta, SemanticTokensDeltaPartialResult]] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect_full_delta(
            self,
            document,
            previous_result_id,
            callback_filter=language_id_filter(document),
            **kwargs,
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        # only the last is returned
        if len(results) > 0:
            return results[-1]

        return None

    @rpc_method(name="textDocument/semanticTokens/range", param_type=SemanticTokensRangeParams)
    @threaded()
    async def _text_document_semantic_tokens_range(
        self, text_document: TextDocumentIdentifier, range: Range, *args: Any, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:

        results: List[Union[SemanticTokens, SemanticTokensPartialResult]] = []

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        for result in await self.collect_range(
            self,
            document,
            range,
            callback_filter=language_id_filter(document),
            **kwargs,
        ):
            if isinstance(result, BaseException):
                if not isinstance(result, CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                if result is not None:
                    results.append(result)

        # only the last is returned
        if len(results) > 0:
            return results[-1]

        return None

    async def refresh(self) -> None:
        if (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.workspace is not None
            and self.parent.client_capabilities.workspace.semantic_tokens is not None
            and self.parent.client_capabilities.workspace.semantic_tokens.refresh_support
        ):
            await self.parent.send_request_async("workspace/semanticTokens/refresh")
