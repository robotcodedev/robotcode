import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from ..._version import __version__
from ...jsonrpc2.protocol import ProtocolPartDescriptor
from ...utils.dataclasses import from_dict
from ...utils.logging import LoggingDescriptor
from ..common.lsp_types import (
    DocumentFilter,
    Model,
    TextDocumentChangeRegistrationOptions,
    TextDocumentRegistrationOptions,
    TextDocumentSyncKind,
)
from ..common.parts.document_symbols import symbol_information_label
from ..common.protocol import LanguageServerProtocol
from .parts.completion import RobotCompletionProtocolPart
from .parts.diagnostics import RobotDiagnosticsProtocolPart
from .parts.discovering import DiscoveringProtocolPart
from .parts.document_symbols import RobotDocumentSymbolsProtocolPart
from .parts.documents_cache import DocumentsCache
from .parts.folding_range import RobotFoldingRangeProtocolPart
from .parts.formatting import RobotFormattingProtocolPart
from .parts.goto import RobotGotoProtocolPart
from .parts.hover import RobotHoverProtocolPart
from .parts.references import RobotReferencesProtocolPart
from .parts.robocop_diagnostics import RobotRoboCopDiagnosticsProtocolPart
from .parts.robot_workspace import RobotWorkspaceProtocolPart
from .parts.semantic_tokens import RobotSemanticTokenProtocolPart
from .parts.signature_help import RobotSignatureHelpProtocolPart
from .utils.version import get_robot_version

if TYPE_CHECKING:
    from .server import RobotLanguageServer


def check_robotframework() -> None:
    try:
        __import__("robot")
    except ImportError as e:
        raise Exception("'robot' module not found, please install RobotFramework.") from e

    if get_robot_version() < (4, 0):
        raise Exception("Wrong RobotFramework version. Expect version >= 4.0")


@dataclass
class Options(Model):
    storage_uri: Optional[str] = None
    global_storage_uri: Optional[str] = None


@symbol_information_label("robotframework")
class RobotLanguageServerProtocol(LanguageServerProtocol):
    _logger = LoggingDescriptor()

    documents_cache = ProtocolPartDescriptor(DocumentsCache)
    robot_diagnostics = ProtocolPartDescriptor(RobotDiagnosticsProtocolPart)
    robot_folding_ranges = ProtocolPartDescriptor(RobotFoldingRangeProtocolPart)
    robot_goto = ProtocolPartDescriptor(RobotGotoProtocolPart)
    robot_hover = ProtocolPartDescriptor(RobotHoverProtocolPart)
    robot_completion = ProtocolPartDescriptor(RobotCompletionProtocolPart)
    robot_signature_help = ProtocolPartDescriptor(RobotSignatureHelpProtocolPart)
    robot_document_symbols = ProtocolPartDescriptor(RobotDocumentSymbolsProtocolPart)
    robot_robocop_diagnostics = ProtocolPartDescriptor(RobotRoboCopDiagnosticsProtocolPart)
    robot_formatting = ProtocolPartDescriptor(RobotFormattingProtocolPart)
    robot_discovering = ProtocolPartDescriptor(DiscoveringProtocolPart)
    robot_semantic_tokens = ProtocolPartDescriptor(RobotSemanticTokenProtocolPart)
    robot_references = ProtocolPartDescriptor(RobotReferencesProtocolPart)
    robot_workspace = ProtocolPartDescriptor(RobotWorkspaceProtocolPart)

    name = "RobotCode"
    version = __version__

    def __init__(self, server: "RobotLanguageServer"):
        super().__init__(server)
        self.options = Options()
        super().on_initialize.add(self._on_initialize)
        super().on_initialized.add(self._on_initialized)

    @_logger.call
    async def _on_initialize(self, sender: Any, initialization_options: Optional[Any] = None) -> None:
        check_robotframework()

        if initialization_options is not None:
            self.options = from_dict(initialization_options, Options)

        self._logger.info(f"initialized with {repr(self.options)}")

    @_logger.call
    async def _on_initialized(self, sender: Any) -> None:
        if (
            self.client_capabilities
            and self.client_capabilities.workspace
            and self.client_capabilities.workspace.file_operations
            and self.client_capabilities.workspace.file_operations.dynamic_registration
        ):
            document_selector = [DocumentFilter(language="python")]
            await self.register_capability(
                str(uuid.uuid4()),
                "textDocument/didOpen",
                TextDocumentRegistrationOptions(document_selector=document_selector),
            )
            await self.register_capability(
                str(uuid.uuid4()),
                "textDocument/didChange",
                TextDocumentChangeRegistrationOptions(
                    document_selector=document_selector, sync_kind=TextDocumentSyncKind.INCREMENTAL
                ),
            )
            await self.register_capability(
                str(uuid.uuid4()),
                "textDocument/didClose",
                TextDocumentRegistrationOptions(document_selector=document_selector),
            )
