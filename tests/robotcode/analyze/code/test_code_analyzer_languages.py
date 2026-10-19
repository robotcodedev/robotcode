"""Tests that `robotcode analyze code` reads a Robot Framework file again after the language settings changed.

What the analysis cache keeps of a file was read with the language settings of
its run. A run with other settings must not use it: a German section header is
a section only when German is one of the languages.
"""

from pathlib import Path
from typing import List, Optional, Sequence

import pytest

from robotcode.analyze.code.code_analyzer import CodeAnalyzer, DocumentDiagnosticReport
from robotcode.analyze.code.robot_framework_language_provider import RobotFrameworkLanguageProvider
from robotcode.plugin import Application
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig
from robotcode.robot.utils import RF_VERSION
from tests.robotcode.language_server.robotframework.tools import write_project

pytestmark = pytest.mark.skipif(RF_VERSION < (6, 0), reason="language settings exist from RF 6.0 on")

PROJECT = {
    "keywords.resource": "*** Schlüsselwörter ***\nMein Keyword\n    No Operation\n",
    "suite.robot": "*** Settings ***\nResource    keywords.resource\n\n*** Test Cases ***\nFirst\n    Mein Keyword\n",
}
NOT_READ = ["KeywordNotFound", "ResourceEmpty"]


def _suite_problems(root: Path, languages: Optional[Sequence[str]]) -> List[str]:
    """Run the analysis as `robotcode analyze code` does and return the codes of the suite's problems."""
    analyzer = CodeAnalyzer(
        app=Application(),
        analysis_config=WorkspaceAnalysisConfig(),
        robot_profile=RobotBaseProfile(languages=[*languages] if languages is not None else None),
        root_folder=root,
    )
    problems: List[str] = []
    for report in analyzer.run():
        if isinstance(report, DocumentDiagnosticReport) and report.document.uri.to_path().name == "suite.robot":
            problems += sorted(str(d.code) for d in report.items)

    provider = next(h for h in analyzer.language_handlers if isinstance(h, RobotFrameworkLanguageProvider))
    folder = analyzer.workspace.workspace_folders[0]
    provider.document_cache.get_imports_manager_for_workspace_folder(folder).data_cache.close()
    return problems


def test_a_language_added_between_two_runs_is_used(tmp_path: Path) -> None:
    write_project(tmp_path, PROJECT)
    assert _suite_problems(tmp_path, None) == NOT_READ

    assert _suite_problems(tmp_path, ["de"]) == []


def test_a_language_removed_between_two_runs_is_not_used_any_more(tmp_path: Path) -> None:
    write_project(tmp_path, PROJECT)
    assert _suite_problems(tmp_path, ["de"]) == []

    assert _suite_problems(tmp_path, None) == NOT_READ
