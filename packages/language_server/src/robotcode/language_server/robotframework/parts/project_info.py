from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from robot.version import get_version

from robotcode.core.utils.dataclasses import CamelSnakeMixin
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method

from .formatting import robotidy_installed
from .protocol_part import RobotLanguageServerProtocolPart
from .robocop_diagnostics import robocop_installed

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass(repr=False)
class ProjectInfo(CamelSnakeMixin):
    robot_version_string: str
    robocop_version_string: Optional[str]
    tidy_version_string: Optional[str] = None


class ProjectInfoPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

    @rpc_method(name="robot/projectInfo", threaded=True)
    @_logger.call
    def _get_document_imports(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ProjectInfo:
        robocop_version_string = None
        if robocop_installed():
            from robocop.version import __version__

            robocop_version_string = __version__

        tidy_version_string = None
        if robotidy_installed():
            from robotidy.version import __version__

            tidy_version_string = __version__

        return ProjectInfo(
            robot_version_string=get_version(),
            robocop_version_string=robocop_version_string,
            tidy_version_string=tidy_version_string,
        )
