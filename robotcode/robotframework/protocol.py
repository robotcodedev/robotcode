from typing import Any, TYPE_CHECKING, Optional

from ..jsonrpc2.protocol import ProtocolPartDescriptor
from ..language_server.protocol import LanguageServerProtocol
from ..language_server.text_document import TextDocument
from .parts.robot_diagnostics import RobotDiagnosticsProtocolPart

if TYPE_CHECKING:
    from .server import RobotLanguageServer


def check_robotframework() -> None:
    try:
        __import__("robot")
    except ImportError as e:
        raise Exception("RobotFramework not found, please install.") from e


class RobotLanguageServerProtocol(LanguageServerProtocol):
    robot_diagnostics = ProtocolPartDescriptor(RobotDiagnosticsProtocolPart[TextDocument])

    def __init__(self, server: Optional["RobotLanguageServer"]):
        super().__init__(server)

    def on_initialize(self, initialization_options: Optional[Any] = None) -> None:
        check_robotframework()
