import asyncio
import threading
from threading import Event
from typing import Any, ClassVar, Final, List, Optional, Set, Union

from robotcode.core.concurrent import Task
from robotcode.core.event import event
from robotcode.core.language import LanguageDefinition
from robotcode.core.lsp.types import (
    CancelParams,
    ClientCapabilities,
    InitializedParams,
    InitializeError,
    InitializeParams,
    InitializeParamsClientInfoType,
    InitializeResult,
    InitializeResultServerInfoType,
    PositionEncodingKind,
    ProgressToken,
    Registration,
    RegistrationParams,
    SaveOptions,
    ServerCapabilities,
    SetTraceParams,
    TextDocumentSyncKind,
    TextDocumentSyncOptions,
    TraceValues,
    Unregistration,
    UnregistrationParams,
    WorkspaceFolder,
)
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.process import pid_exists
from robotcode.jsonrpc2.protocol import (
    JsonRPCErrorException,
    JsonRPCErrors,
    JsonRPCException,
    JsonRPCProtocol,
    ProtocolPartDescriptor,
    rpc_method,
)
from robotcode.jsonrpc2.server import JsonRPCServer

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
from .parts.protocol_part import LanguageServerProtocolPart
from .parts.references import ReferencesProtocolPart
from .parts.rename import RenameProtocolPart
from .parts.selection_range import SelectionRangeProtocolPart
from .parts.semantic_tokens import SemanticTokensProtocolPart
from .parts.signature_help import SignatureHelpProtocolPart
from .parts.window import WindowProtocolPart
from .parts.workspace import Workspace

__all__ = ["LanguageServerException", "LanguageServerProtocol"]


class LanguageServerException(JsonRPCException):
    pass


class LanguageServerProtocol(JsonRPCProtocol):
    __logger = LoggingDescriptor()

    commands: Final = ProtocolPartDescriptor(CommandsProtocolPart)
    window: Final = ProtocolPartDescriptor(WindowProtocolPart)
    documents: Final = ProtocolPartDescriptor(TextDocumentProtocolPart)
    diagnostics: Final = ProtocolPartDescriptor(DiagnosticsProtocolPart)
    folding_ranges: Final = ProtocolPartDescriptor(FoldingRangeProtocolPart)
    definition: Final = ProtocolPartDescriptor(DefinitionProtocolPart)
    implementation: Final = ProtocolPartDescriptor(ImplementationProtocolPart)
    declaration: Final = ProtocolPartDescriptor(DeclarationProtocolPart)
    hover: Final = ProtocolPartDescriptor(HoverProtocolPart)
    completion: Final = ProtocolPartDescriptor(CompletionProtocolPart)
    signature_help: Final = ProtocolPartDescriptor(SignatureHelpProtocolPart)
    code_lens: Final = ProtocolPartDescriptor(CodeLensProtocolPart)
    document_symbols: Final = ProtocolPartDescriptor(DocumentSymbolsProtocolPart)
    formatting: Final = ProtocolPartDescriptor(FormattingProtocolPart)
    semantic_tokens: Final = ProtocolPartDescriptor(SemanticTokensProtocolPart)
    references: Final = ProtocolPartDescriptor(ReferencesProtocolPart)
    document_highlight: Final = ProtocolPartDescriptor(DocumentHighlightProtocolPart)
    linked_editing_range: Final = ProtocolPartDescriptor(LinkedEditingRangeProtocolPart)
    selection_range: Final = ProtocolPartDescriptor(SelectionRangeProtocolPart)
    rename: Final = ProtocolPartDescriptor(RenameProtocolPart)
    inline_value: Final = ProtocolPartDescriptor(InlineValueProtocolPart)
    inlay_hint: Final = ProtocolPartDescriptor(InlayHintProtocolPart)
    code_action: Final = ProtocolPartDescriptor(CodeActionProtocolPart)

    name: Optional[str] = None
    short_name: Optional[str] = None
    progress_title: Optional[str] = None
    version: Optional[str] = None

    file_extensions: ClassVar[Set[str]] = set()
    languages: ClassVar[List[LanguageDefinition]] = []

    def __init__(self, server: JsonRPCServer[Any]):
        super().__init__()
        self.running_thread = threading.current_thread()
        self.server = server
        self.parent_process_id: Optional[int] = None
        self.initialization_options: Any = None
        self.client_info: Optional[InitializeParamsClientInfoType] = None
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

        self._trace = TraceValues.OFF
        self.is_initialized = Event()

    @event
    def on_shutdown(sender) -> None:  # pragma: no cover, NOSONAR
        ...

    @event
    def on_exit(sender) -> None:  # pragma: no cover, NOSONAR
        ...

    @property
    def trace(self) -> TraceValues:
        return self._trace

    @trace.setter
    def trace(self, value: TraceValues) -> None:
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
            if isinstance(p, LanguageServerProtocolPart):
                p.extend_capabilities(base_capabilities)

        return base_capabilities

    PARENT_PROCESS_WATCHER_INTERVAL = 5

    def start_parent_process_watcher(self) -> None:
        if self.parent_process_id and self.loop:
            self.loop.call_later(
                self.PARENT_PROCESS_WATCHER_INTERVAL,
                self._parent_process_watcher,
            )

    def _parent_process_watcher(self) -> None:
        if not self.parent_process_id:
            return
        if not pid_exists(self.parent_process_id):
            self.__logger.error(lambda: f"Parent process {self.parent_process_id} is dead, exiting...")
            exit(2)
        self.start_parent_process_watcher()

    @rpc_method(name="initialize", param_type=InitializeParams)
    @__logger.call
    def _initialize(
        self,
        capabilities: ClientCapabilities,
        root_path: Optional[str] = None,
        root_uri: Optional[str] = None,
        initialization_options: Optional[Any] = None,
        trace: Optional[TraceValues] = None,
        client_info: Optional[InitializeParamsClientInfoType] = None,
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
        work_done_token: Optional[ProgressToken] = None,
        process_id: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> InitializeResult:
        self.parent_process_id = process_id
        if self.parent_process_id and pid_exists(self.parent_process_id):
            self.start_parent_process_watcher()

        self.trace = trace or TraceValues.OFF
        self.client_info = client_info

        self.client_capabilities = capabilities

        self._workspace = Workspace(
            self,
            root_uri=root_uri,
            root_path=root_path,
            workspace_folders=workspace_folders,
        )

        folders = (
            ", ".join(f"'{v.name}'" for v in self._workspace.workspace_folders)
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
                    and PositionEncodingKind.UTF16 in self.client_capabilities.general.position_encodings
                ):
                    self.capabilities.position_encoding = PositionEncodingKind.UTF16

                self.on_initialize(self, initialization_options)
            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except JsonRPCErrorException:
                raise
            except BaseException as e:
                raise JsonRPCErrorException(
                    JsonRPCErrors.INTERNAL_ERROR,
                    f"Can't start language server: {e}",
                    InitializeError(retry=False),
                ) from e

            return InitializeResult(
                capabilities=self.capabilities,
                **(
                    {"server_info": InitializeResultServerInfoType(name=self.name, version=self.version)}
                    if self.name is not None
                    else {}
                ),
            )
        finally:
            self.window.progress_end(work_done_token)

    @event
    def on_initialize(sender, initialization_options: Optional[Any] = None) -> None:  # pragma: no cover, NOSONAR
        ...

    @rpc_method(name="initialized", param_type=InitializedParams, threaded=True)
    def _initialized(self, params: InitializedParams, *args: Any, **kwargs: Any) -> None:
        if self.is_initialized.is_set():
            return

        self.on_initialized(self)

        self.is_initialized.set()

    def ensure_initialized(self) -> None:
        if not self.is_initialized.wait(60):
            raise RuntimeError("Language server not initialized")

    @event
    def on_initialized(sender) -> None:  # pragma: no cover, NOSONAR
        ...

    @rpc_method(name="shutdown", cancelable=False)
    @__logger.call
    def _shutdown(self, *args: Any, **kwargs: Any) -> None:
        if self.shutdown_received:
            return

        self.shutdown_received = True

        try:
            self.cancel_all_received_request()
        except BaseException as e:
            self.__logger.exception(e)

        self.on_shutdown(self)

    @rpc_method(name="exit")
    @__logger.call
    def _exit(self, *args: Any, **kwargs: Any) -> None:
        self.on_exit(self)

        exit(0 if self.shutdown_received else 1)

    @rpc_method(name="$/setTrace", param_type=SetTraceParams)
    @__logger.call
    def _set_trace(self, value: TraceValues, *args: Any, **kwargs: Any) -> None:
        self.trace = value

    @rpc_method(name="$/cancelRequest", param_type=CancelParams)
    @__logger.call
    def _cancel_request(self, id: Union[int, str], **kwargs: Any) -> None:
        self.cancel_request(id)

    def register_capability(self, id: str, method: str, register_options: Optional[Any]) -> Task[None]:
        return self.register_capabilities([Registration(id=id, method=method, register_options=register_options)])

    def register_capabilities(self, registrations: List[Registration]) -> Task[None]:
        if not registrations:
            result: Task[None] = Task()
            result.set_result(None)
            return result
        return self.send_request(
            "client/registerCapability",
            RegistrationParams(registrations=registrations),
        )

    def unregister_capability(self, id: str, method: str) -> Task[None]:
        return self.unregister_capabilities([Unregistration(id=id, method=method)])

    def unregister_capabilities(self, unregisterations: List[Unregistration]) -> Task[None]:
        if not unregisterations:
            result: Task[None] = Task()
            result.set_result(None)
            return result
        return self.send_request(
            "client/unregisterCapability",
            UnregistrationParams(unregisterations=unregisterations),
        )
