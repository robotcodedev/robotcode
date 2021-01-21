from typing import TYPE_CHECKING, Any, Optional

from ..jsonrpc2.protocol import ProtocolPartDescriptor
from ..language_server.protocol import LanguageServerProtocol
from ..language_server.types import Model
from ..utils.logging import LoggingDescriptor
from .parts.diagnostics import RobotDiagnosticsProtocolPart
from .parts.folding_range import RobotFoldingRangeProtocolPart
from .parts.definition import RobotDefinitionProtocolPart
from .parts.hover import RobotHoverProtocolPart
from .parts.model_token_cache import ModelTokenCache

if TYPE_CHECKING:
    from .server import RobotLanguageServer


def check_robotframework() -> None:
    try:
        __import__("robot")
    except ImportError as e:
        raise Exception("RobotFramework not found, please install.") from e


class Options(Model):
    storage_uri: Optional[str] = None
    global_storage_uri: Optional[str] = None


class RobotLanguageServerProtocol(LanguageServerProtocol):
    _logger = LoggingDescriptor()

    model_token_cache = ProtocolPartDescriptor(ModelTokenCache)
    _robot_diagnostics = ProtocolPartDescriptor(RobotDiagnosticsProtocolPart)
    _robot_folding_ranges = ProtocolPartDescriptor(RobotFoldingRangeProtocolPart)
    _robot_definition = ProtocolPartDescriptor(RobotDefinitionProtocolPart)
    _robot_hover = ProtocolPartDescriptor(RobotHoverProtocolPart)

    def __init__(self, server: "RobotLanguageServer"):
        super().__init__(server)
        self.options = Options()

    @_logger.call
    def on_initialize(self, initialization_options: Optional[Any] = None) -> None:
        check_robotframework()

        if initialization_options is not None:
            self.options = Options.parse_obj(initialization_options)

        self._logger.info(f"initialized with {repr(self.options)}")
