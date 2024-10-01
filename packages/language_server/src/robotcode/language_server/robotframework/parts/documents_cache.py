import threading
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.workspace import WorkspaceFolder
from robotcode.robot.diagnostics.document_cache_helper import DocumentsCacheHelper
from robotcode.robot.diagnostics.imports_manager import ImportsManager
from robotcode.robot.diagnostics.workspace_config import CacheConfig, CacheSaveLocation
from robotcode.robot.utils.stubs import Languages

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class UnknownFileTypeError(Exception):
    pass


class DocumentsCachePart(RobotLanguageServerProtocolPart, DocumentsCacheHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)
        DocumentsCacheHelper.__init__(
            self, parent.workspace, parent.documents, parent.workspace, parent.robot_profile, parent.analysis_config
        )

        self._imports_managers_lock = threading.RLock()
        self._imports_managers: weakref.WeakKeyDictionary[WorkspaceFolder, ImportsManager] = weakref.WeakKeyDictionary()
        self._default_imports_manager: Optional[ImportsManager] = None
        self._workspace_languages: weakref.WeakKeyDictionary[WorkspaceFolder, Optional[Languages]] = (
            weakref.WeakKeyDictionary()
        )

    def calc_cache_path(self, folder_uri: Uri) -> Path:
        cache_config = self.parent.workspace.get_configuration(CacheConfig, folder_uri)
        cache_base_path = folder_uri.to_path()
        if (
            cache_config.save_location == CacheSaveLocation.WORKSPACE_STORAGE
            and isinstance(self.parent.initialization_options, dict)
            and "storageUri" in self.parent.initialization_options
        ):
            cache_base_path = Uri(self.parent.initialization_options["storageUri"]).to_path()
        return cache_base_path
