import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from robot.version import get_version

from robotcode.core.utils.dataclasses import CamelSnakeMixin
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method

from ...__version__ import __version__ as robotcode_version
from .protocol_part import RobotLanguageServerProtocolPart
from .robocop_tidy_mixin import RoboCopTidyMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass(repr=False)
class ProjectInfo(CamelSnakeMixin):
    robot_version_string: str
    robocop_version_string: Optional[str]
    tidy_version_string: Optional[str] = None
    python_version_string: Optional[str] = None
    python_executable: Optional[str] = None
    robot_code_version_string: Optional[str] = None


class ProjectInfoPart(RobotLanguageServerProtocolPart, RoboCopTidyMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

    @rpc_method(name="robot/projectInfo", threaded=True)
    @_logger.call
    def _robot_project_info(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ProjectInfo:
        robocop_version_string = None
        if self.robocop_installed:
            robocop_version_string = self.robocop_version_str

        tidy_version_string = None
        if self.robotidy_installed:
            tidy_version_string = self.robotidy_version_str

        return ProjectInfo(
            robot_version_string=get_version(),
            robocop_version_string=robocop_version_string,
            tidy_version_string=tidy_version_string,
            python_version_string=sys.version,
            python_executable=sys.executable,
            robot_code_version_string=robotcode_version,
        )
