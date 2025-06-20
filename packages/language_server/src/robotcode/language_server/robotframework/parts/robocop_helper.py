import functools
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Union

from robotcode.core.lsp.types import MessageType
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.version import Version, create_version_from_str
from robotcode.core.workspace import WorkspaceFolder

from ..configuration import RoboCopConfig
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

if TYPE_CHECKING:
    from robocop.config import ConfigManager


class RobocopConfigError(Exception):
    """Robocop configuration errors."""


class RoboCopHelper(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)
        self._config_managers: Dict[WorkspaceFolder, "ConfigManager"] = {}

    @functools.cached_property
    def robotidy_installed(self) -> bool:
        try:
            __import__("robotidy")
        except ImportError:
            return False
        return True

    @functools.cached_property
    def robotidy_version(self) -> Version:
        from robotidy.version import __version__

        return create_version_from_str(__version__)

    @functools.cached_property
    def robotidy_version_str(self) -> str:
        from robotidy.version import __version__

        return str(__version__)

    @functools.cached_property
    def robocop_installed(self) -> bool:
        try:
            __import__("robocop")
        except ImportError:
            return False
        return True

    @functools.cached_property
    def robocop_version(self) -> Version:
        from robocop import __version__

        return create_version_from_str(__version__)

    @functools.cached_property
    def robocop_version_str(self) -> str:
        from robocop import __version__

        return str(__version__)

    def get_robocop_config(self, resource: Union[TextDocument, WorkspaceFolder]) -> RoboCopConfig:
        folder = (
            self.parent.workspace.get_workspace_folder(resource.uri) if isinstance(resource, TextDocument) else resource
        )
        if folder is None:
            return RoboCopConfig()

        return self.parent.workspace.get_configuration(RoboCopConfig, folder.uri)

    def get_config_manager(self, workspace_folder: WorkspaceFolder) -> "ConfigManager":
        from robocop.config import ConfigManager

        if workspace_folder in self._config_managers:
            return self._config_managers[workspace_folder]

        config = self.get_robocop_config(workspace_folder)

        result = None
        try:
            config_path = None

            if config.config_file:
                config_path = Path(config.config_file)
                if not config_path.exists():
                    raise RobocopConfigError(f"Config file {config_path} does not exist.")

            result = ConfigManager(
                [],
                root=workspace_folder.uri.to_path(),
                config=config_path,
                ignore_git_dir=config.ignore_git_dir,
                ignore_file_config=config.ignore_file_config,
            )
            self._config_managers[workspace_folder] = result
            return result
        except Exception as e:
            self._logger.exception(e)
            e_msg = str(e)
            error_details = f": {e_msg}" if e_msg else ""
            self.parent.window.show_message(
                f"Robocop configuration could not be loaded{error_details}. "
                f"Please verify your configuration files "
                f"and workspace settings. Check the output logs for detailed error information.",
                MessageType.ERROR,
            )
            raise RobocopConfigError(f"Failed to load Robocop configuration: {e} ({e.__class__.__qualname__})") from e
