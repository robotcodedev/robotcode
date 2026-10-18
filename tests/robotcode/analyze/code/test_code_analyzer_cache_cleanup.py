"""Tests that `robotcode analyze code` removes the cache entries of deleted files after a run.

The language server and runs on other paths share the cache, so a run removes
only the entries of files that do not exist, also outside the paths it
analyzed.
"""

from pathlib import Path
from typing import Iterable, Set

from robotcode.analyze.code.code_analyzer import CodeAnalyzer
from robotcode.analyze.code.robot_framework_language_provider import RobotFrameworkLanguageProvider
from robotcode.plugin import Application
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.data_cache import CacheSection
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig
from tests.robotcode.language_server.robotframework.tools import write_project

SUITE = "*** Test Cases ***\nFirst\n    Log    hello\n"


def _analyze(root: Path, paths: Iterable[Path] = ()) -> Set[str]:
    """Run the analysis as `robotcode analyze code` does, and return the names of the files with cache entries."""
    analyzer = CodeAnalyzer(
        app=Application(),
        analysis_config=WorkspaceAnalysisConfig(),
        robot_profile=RobotBaseProfile(),
        root_folder=root,
    )
    for _ in analyzer.run(paths=list(paths)):
        pass

    provider = next(h for h in analyzer.language_handlers if isinstance(h, RobotFrameworkLanguageProvider))
    folder = analyzer.workspace.workspace_folders[0]
    data_cache = provider.document_cache.get_imports_manager_for_workspace_folder(folder).data_cache
    try:
        return {
            Path(entry.entry_name.split("\n", 1)[0]).name
            for section in (CacheSection.NAMESPACE, CacheSection.RESOURCE)
            for entry in data_cache.list_entries(section)
        }
    finally:
        data_cache.close()


def test_a_suite_deleted_between_two_runs_has_no_entries_after_the_second(tmp_path: Path) -> None:
    write_project(tmp_path, {"a.robot": SUITE, "b.robot": SUITE})
    assert {"a.robot", "b.robot"} <= _analyze(tmp_path)

    (tmp_path / "b.robot").unlink()

    cached = _analyze(tmp_path)
    assert "b.robot" not in cached
    assert "a.robot" in cached


def test_a_run_on_one_folder_keeps_the_entries_of_existing_files_in_another(tmp_path: Path) -> None:
    write_project(tmp_path, {"area_a/x.robot": SUITE, "area_b/y.robot": SUITE, "area_b/z.robot": SUITE})
    assert {"x.robot", "y.robot", "z.robot"} <= _analyze(tmp_path)

    (tmp_path / "area_b" / "z.robot").unlink()

    cached = _analyze(tmp_path, [tmp_path / "area_a"])
    assert {"x.robot", "y.robot"} <= cached
    assert "z.robot" not in cached
