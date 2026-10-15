"""Where the language server keeps its cache: `cache-dir` of the robot.toml wins over the editor's storage."""

from pathlib import Path
from typing import Any, Optional, cast
from unittest.mock import MagicMock

from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.parts.documents_cache import DocumentsCachePart
from robotcode.robot.diagnostics.workspace_config import CacheConfig, CacheSaveLocation, WorkspaceAnalysisConfig


def _part(cache_dir: Optional[str], storage: Path) -> DocumentsCachePart:
    """A documents cache part of a server whose editor asks for its workspace storage."""
    part: Any = object.__new__(DocumentsCachePart)
    part.analysis_config = WorkspaceAnalysisConfig(cache_dir=cache_dir)
    parent = MagicMock()
    parent.workspace.get_configuration.return_value = CacheConfig(save_location=CacheSaveLocation.WORKSPACE_STORAGE)
    parent.initialization_options = {"storageUri": str(Uri.from_path(storage))}
    part._parent = parent
    return cast(DocumentsCachePart, part)


def test_cache_path_is_the_editor_storage_without_cache_dir(tmp_path: Path) -> None:
    storage = Uri.from_path(tmp_path / "storage")

    assert _part(None, tmp_path / "storage").calc_cache_path(Uri.from_path(tmp_path / "project")) == storage.to_path()


def test_cache_dir_wins_over_the_editor_storage(tmp_path: Path) -> None:
    folder = Uri.from_path(tmp_path / "project")

    assert _part("mycache", tmp_path / "storage").calc_cache_path(folder) == folder.to_path() / "mycache"
