from __future__ import annotations

import asyncio
from typing import Any, List, NamedTuple, Optional, Set, Union, cast

from ...jsonrpc2.protocol import (
    JsonRPCErrorException,
    JsonRPCErrors,
    JsonRPCException,
    JsonRPCProtocol,
    ProtocolPartDescriptor,
    rpc_method,
)
from ...jsonrpc2.server import JsonRPCServer
from ...utils.async_tools import async_event
from ...utils.logging import LoggingDescriptor
from .has_extend_capabilities import HasExtendCapabilities
from .lsp_types import (
    UTF16,
    CancelParams,
    ClientCapabilities,
    ClientInfo,
    InitializedParams,
    InitializeError,
    InitializeParams,
    InitializeResult,
    InitializeResultServerInfo,
    ProgressToken,
    Registration,
    RegistrationParams,
    SaveOptions,
    ServerCapabilities,
    SetTraceParams,
    TextDocumentSyncKind,
    TextDocumentSyncOptions,
    TraceValue,
    Unregistration,
    UnregistrationParams,
    WorkspaceFolder,
)
from .parts.code_action import CodeActionProtocolPart
from .parts.code_lens import CodeLensProtocolPart
from .parts.commands import CommandsProtocolPart
from .parts.completion import CompletionProtocolPart
from .parts.declaration import DeclarationProtocolPart
from .parts.definition import DefinitionProtocolPart
from .parts.diagnostics import DiagnosticsProtocolPart
from .parts.document_highlight import DocumentHighlightProtocolPart
from .parts.document_symbols import DocumentSymbolsProtocolPart
from .parts.documents import TextDocumentProtocolPart
from .parts.folding_range import FoldingRangeProtocolPart
from .parts.formatting import FormattingProtocolPart
from .parts.hover import HoverProtocolPart
from .parts.implementation import ImplementationProtocolPart
from .parts.inlay_hint import InlayHintProtocolPart
from .parts.inline_value import InlineValueProtocolPart
from .parts.linked_editing_ranges import LinkedEditingRangeProtocolPart
from .parts.references import ReferencesProtocolPart
from .parts.rename import RenameProtocolPart
from .parts.selection_range import SelectionRangeProtocolPart
from .parts.semantic_tokens import SemanticTokensProtocolPart
from .parts.signature_help import SignatureHelpProtocolPart
from .parts.window import WindowProtocolPart
from .parts.workspace import Workspace

__all__ = ["LanguageServerException", "LanguageServerProtocol", "HasExtendCapabilities"]


class LanguageServerException(JsonRPCException):
    pass


class LanguageDefinition(NamedTuple):
    id: str
    extensions: List[str]
    aliases: Optional[List[str]] = None


class LanguageServerProtocol(JsonRPCProtocol):

    _logger = LoggingDescriptor()

    commands = ProtocolPartDescriptor(CommandsProtocolPart)
    window = ProtocolPartDescriptor(WindowProtocolPart)
    documents = ProtocolPartDescriptor(TextDocumentProtocolPart)
    diagnostics = ProtocolPartDescriptor(DiagnosticsProtocolPart)
    folding_ranges = ProtocolPartDescriptor(FoldingRangeProtocolPart)
    definition = ProtocolPartDescriptor(DefinitionProtocolPart)
    implementation = ProtocolPartDescriptor(ImplementationProtocolPart)
    declaration = ProtocolPartDescriptor(DeclarationProtocolPart)
    hover = ProtocolPartDescriptor(HoverProtocolPart)
    completion = ProtocolPartDescriptor(CompletionProtocolPart)
    signature_help = ProtocolPartDescriptor(SignatureHelpProtocolPart)
    code_lens = ProtocolPartDescriptor(CodeLensProtocolPart)
    document_symbols = ProtocolPartDescriptor(DocumentSymbolsProtocolPart)
    formatting = ProtocolPartDescriptor(FormattingProtocolPart)
    semantic_tokens = ProtocolPartDescriptor(SemanticTokensProtocolPart)
    references = ProtocolPartDescriptor(ReferencesProtocolPart)
    document_highlight = ProtocolPartDescriptor(DocumentHighlightProtocolPart)
    linked_editing_range = ProtocolPartDescriptor(LinkedEditingRangeProtocolPart)
    selection_range = ProtocolPartDescriptor(SelectionRangeProtocolPart)
    rename = ProtocolPartDescriptor(RenameProtocolPart)
    inline_value = ProtocolPartDescriptor(InlineValueProtocolPart)
    inlay_hint = ProtocolPartDescriptor(InlayHintProtocolPart)
    code_action = ProtocolPartDescriptor(CodeActionProtocolPart)

    name: Optional[str] = None
    short_name: Optional[str] = None
    version: Optional[str] = None

    file_extensions: Set[str] = set()
    languages: List[LanguageDefinition] = []

    def __init__(self, server: JsonRPCServer[Any]):
        super().__init__()
        self.server = server

        self.initialization_options: Any = None
        self.client_info: Optional[ClientInfo] = None
        self._workspace: Optional[Workspace] = None
        self.client_capabilities: Optional[ClientCapabilities] = None
        self.shutdown_received = False
        self._capabilities: Optional[ServerCapabilities] = None
        self._base_capabilities = ServerCapabilities(
            text_document_sync=TextDocumentSyncOptions(
                open_close=True,
                change=TextDocumentSyncKind.INCREMENTAL,
                will_save=True,
                will_save_wait_until=True,
                save=SaveOptions(include_text=True),
            )
        )

        self._trace = TraceValue.OFF
        self._is_initialized = False

    @async_event
    async def on_shutdown(sender) -> None:  # pragma: no cover, NOSONAR
        ...

    @async_event
    async def on_exit(sender) -> None:  # pragma: no cover, NOSONAR
        ...

    @property
    def trace(self) -> TraceValue:
        return self._trace

    @trace.setter
    def trace(self, value: TraceValue) -> None:
        self._trace = value

    @property
    def workspace(self) -> Workspace:
        if self._workspace is None:
            raise LanguageServerException(f"{type(self).__name__} not initialized")

        return self._workspace

    @property
    def capabilities(self) -> ServerCapabilities:
        if self._capabilities is None:
            self._capabilities = self._collect_capabilities()
        return self._capabilities

    def _collect_capabilities(self) -> ServerCapabilities:
        from dataclasses import replace

        base_capabilities = replace(self._base_capabilities)

        for p in self.registry.parts:
            if isinstance(p, HasExtendCapabilities):
                cast(HasExtendCapabilities, p).extend_capabilities(base_capabilities)

        return base_capabilities

    @rpc_method(name="initialize", param_type=InitializeParams)
    @_logger.call
    async def _initialize(
        self,
        capabilities: ClientCapabilities,
        root_path: Optional[str] = None,
        root_uri: Optional[str] = None,
        initialization_options: Optional[Any] = None,
        trace: Optional[TraceValue] = None,
        client_info: Optional[ClientInfo] = None,
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
        work_done_token: Optional[ProgressToken] = None,
        *args: Any,
        **kwargs: Any,
    ) -> InitializeResult:

        self.trace = trace or TraceValue.OFF
        self.client_info = client_info

        self.client_capabilities = capabilities

        self._workspace = Workspace(self, root_uri=root_uri, root_path=root_path, workspace_folders=workspace_folders)

        folders = (
            ", ".join((f"'{v.name}'" for v in self._workspace.workspace_folders))
            if self._workspace.workspace_folders
            else ""
        )

        self.window.progress_begin(work_done_token, f"Initialize {folders}...")

        try:
            self.initialization_options = initialization_options
            try:
                if (
                    self.client_capabilities.general
                    and self.client_capabilities.general.position_encodings
                    and UTF16 in self.client_capabilities.general.position_encodings
                ):
                    self.capabilities.position_encoding = UTF16

                await self.on_initialize(self, initialization_options)
            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except JsonRPCErrorException:
                raise
            except BaseException as e:
                raise JsonRPCErrorException(
                    JsonRPCErrors.INTERNAL_ERROR, f"Can't start language server: {e}", InitializeError(retry=False)
                ) from e

            return InitializeResult(
                capabilities=self.capabilities,
                **(
                    {"server_info": InitializeResultServerInfo(name=self.name, version=self.version)}
                    if self.name is not None
                    else {}
                ),
            )
        finally:
            self.window.progress_end(work_done_token)

    @async_event
    async def on_initialize(sender, initialization_options: Optional[Any] = None) -> None:  # pragma: no cover, NOSONAR
        ...

    @rpc_method(name="initialized", param_type=InitializedParams)
    async def _initialized(self, params: InitializedParams, *args: Any, **kwargs: Any) -> None:
        await self.on_initialized(self)

        self._is_initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @async_event
    async def on_initialized(sender) -> None:  # pragma: no cover, NOSONAR
        ...

    @rpc_method(name="shutdown", cancelable=False)
    @_logger.call
    async def _shutdown(self, *args: Any, **kwargs: Any) -> None:
        if self.shutdown_received:
            return

        self.shutdown_received = True

        try:
            await asyncio.wait_for(self.cancel_all_received_request(), 1)
        except BaseException as e:  # NOSONAR
            self._logger.exception(e)

        await self.on_shutdown(self)

    @rpc_method(name="exit")
    @_logger.call
    async def _exit(self, *args: Any, **kwargs: Any) -> None:
        await self.on_exit(self)

        raise SystemExit(0 if self.shutdown_received else 1)

    @rpc_method(name="$/setTrace", param_type=SetTraceParams)
    @_logger.call
    async def _set_trace(self, value: TraceValue, *args: Any, **kwargs: Any) -> None:
        self.trace = value

    @rpc_method(name="$/cancelRequest", param_type=CancelParams)
    @_logger.call
    async def _cancel_request(self, id: Union[int, str], **kwargs: Any) -> None:
        self.cancel_request(id)

    async def register_capability(self, id: str, method: str, register_options: Optional[Any]) -> None:
        await self.register_capabilities([Registration(id=id, method=method, register_options=register_options)])

    async def register_capabilities(self, registrations: List[Registration]) -> None:
        if not registrations:
            return
        await self.send_request_async("client/registerCapability", RegistrationParams(registrations=registrations))

    async def unregister_capability(self, id: str, method: str) -> None:
        await self.unregister_capabilities([Unregistration(id=id, method=method)])

    async def unregister_capabilities(self, unregisterations: List[Unregistration]) -> None:
        if not unregisterations:
            return
        await self.send_request_async(
            "client/unregisterCapability", UnregistrationParams(unregisterations=unregisterations)
        )
