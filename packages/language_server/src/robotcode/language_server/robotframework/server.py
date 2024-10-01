from typing import Optional

from robotcode.core.types import ServerMode, TcpParams
from robotcode.language_server.common.server import (
    TCP_DEFAULT_PORT,
    LanguageServerBase,
)
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig

from .protocol import RobotLanguageServerProtocol


class RobotLanguageServer(LanguageServerBase[RobotLanguageServerProtocol]):
    def __init__(
        self,
        mode: ServerMode = ServerMode.STDIO,
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
        pipe_name: Optional[str] = None,
        profile: Optional[RobotBaseProfile] = None,
        analysis_config: Optional[WorkspaceAnalysisConfig] = None,
    ):
        super().__init__(mode, tcp_params, pipe_name)
        self.profile = profile
        self.analysis_config = analysis_config

    def create_protocol(self) -> RobotLanguageServerProtocol:
        return RobotLanguageServerProtocol(self, self.profile, self.analysis_config)
