from ..common.server import LanguageServerBase
from .protocol import RobotLanguageServerProtocol


class RobotLanguageServer(LanguageServerBase[RobotLanguageServerProtocol]):
    def create_protocol(self) -> RobotLanguageServerProtocol:
        return RobotLanguageServerProtocol(self)
