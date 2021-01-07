from typing import TYPE_CHECKING, Any, Optional

from ..jsonrpc2.protocol import ProtocolPartDescriptor
from ..language_server.protocol import LanguageServerProtocol
from .parts.model_cache import ModelCache
from .parts.diagnostics import RobotDiagnosticsProtocolPart
from .parts.folding_range import RobotFoldingRangeProtocolPart

if TYPE_CHECKING:
    from .server import RobotLanguageServer


def check_robotframework() -> None:
    try:
        __import__("robot")
    except ImportError as e:
        raise Exception("RobotFramework not found, please install.") from e


class RobotLanguageServerProtocol(LanguageServerProtocol):

    model_cache = ProtocolPartDescriptor(ModelCache)
    robot_diagnostics = ProtocolPartDescriptor(RobotDiagnosticsProtocolPart)
    folding_ranges = ProtocolPartDescriptor(RobotFoldingRangeProtocolPart)

    def __init__(self, server: Optional["RobotLanguageServer"]):
        super().__init__(server)

    def on_initialize(self, initialization_options: Optional[Any] = None) -> None:
        check_robotframework()
