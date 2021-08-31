import uuid
from typing import TYPE_CHECKING, Any, Optional

from ..._version import __version__
from ...jsonrpc2.protocol import ProtocolPartDescriptor
from ...utils.logging import LoggingDescriptor
from ..common.protocol import LanguageServerProtocol
from ..common.types import (
    DocumentFilter,
    Model,
    TextDocumentChangeRegistrationOptions,
    TextDocumentRegistrationOptions,
    TextDocumentSyncKind,
)
from .parts.completion import RobotCompletionProtocolPart
from .parts.diagnostics import RobotDiagnosticsProtocolPart
from .parts.discovering import DiscoveringProtocolPart
from .parts.document_symbols import RobotDocumentSymbolsProtocolPart
from .parts.documents_cache import DocumentsCache
from .parts.folding_range import RobotFoldingRangeProtocolPart
from .parts.formatting import RobotFormattingProtocolPart
from .parts.goto import RobotGotoProtocolPart
from .parts.hover import RobotHoverProtocolPart
from .parts.robocop_diagnostics import RobotRoboCopDiagnosticsProtocolPart
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


class Options(Model):
    storage_uri: Optional[str] = None
    global_storage_uri: Optional[str] = None


class RobotLanguageServerProtocol(LanguageServerProtocol):
    _logger = LoggingDescriptor()

    documents_cache = ProtocolPartDescriptor(DocumentsCache)
    _robot_diagnostics = ProtocolPartDescriptor(RobotDiagnosticsProtocolPart)
    _robot_folding_ranges = ProtocolPartDescriptor(RobotFoldingRangeProtocolPart)
    _robot_goto = ProtocolPartDescriptor(RobotGotoProtocolPart)
    _robot_hover = ProtocolPartDescriptor(RobotHoverProtocolPart)
    _robot_completion = ProtocolPartDescriptor(RobotCompletionProtocolPart)
    _robot_signature_help = ProtocolPartDescriptor(RobotSignatureHelpProtocolPart)
    _robot_document_symbols = ProtocolPartDescriptor(RobotDocumentSymbolsProtocolPart)
    _robot_robocop_diagnostics = ProtocolPartDescriptor(RobotRoboCopDiagnosticsProtocolPart)
    _robot_formatting = ProtocolPartDescriptor(RobotFormattingProtocolPart)
    _robot_discovering = ProtocolPartDescriptor(DiscoveringProtocolPart)

    name = "RobotCode"
    version = __version__

    symbol_information_label = "robotframework"

    def __init__(self, server: "RobotLanguageServer"):
        super().__init__(server)
        self.options = Options()
        super().on_initialize.add(self._on_initialize)
        super().on_initialized.add(self._on_initialized)

    @_logger.call
    async def _on_initialize(self, sender: Any, initialization_options: Optional[Any] = None) -> None:
        check_robotframework()

        if initialization_options is not None:
            self.options = Options.parse_obj(initialization_options)

        self._logger.info(f"initialized with {repr(self.options)}")

    @_logger.call
    async def _on_initialized(self, sender: Any) -> None:
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
