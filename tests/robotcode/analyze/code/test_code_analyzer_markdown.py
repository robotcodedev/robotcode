"""Tests that `robotcode analyze code` checks the Markdown files Robot Framework parses like `.robot` files."""

from pathlib import Path
from typing import Dict, List

import pytest

from robotcode.analyze.code.code_analyzer import CodeAnalyzer, DocumentDiagnosticReport
from robotcode.analyze.code.robot_framework_language_provider import RobotFrameworkLanguageProvider
from robotcode.plugin import Application
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig
from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from tests.robotcode.language_server.robotframework.tools import write_project

pytestmark = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")

SHOP = """\
# Shop

```robot
*** Test Cases ***
Buy
    Undefined Keyword
```
"""


def test_the_markdown_suites_robot_framework_parses_are_analysed(tmp_path: Path) -> None:
    write_project(tmp_path, {"shop.robot.md": SHOP, "README.md": SHOP})
    analyzer = CodeAnalyzer(
        app=Application(),
        analysis_config=WorkspaceAnalysisConfig(),
        robot_profile=RobotBaseProfile(),
        root_folder=tmp_path,
    )
    try:
        folder = analyzer.workspace.workspace_folders[0]
        analysed = [d.uri.to_path().name for d in analyzer.collect_documents(folder)]

        problems: Dict[str, List[str]] = {}
        for report in analyzer.run():
            if isinstance(report, DocumentDiagnosticReport):
                problems[report.document.uri.to_path().name] = sorted(str(d.code) for d in report.items)
    finally:
        provider = next(h for h in analyzer.language_handlers if isinstance(h, RobotFrameworkLanguageProvider))
        provider.document_cache.get_imports_manager_for_workspace_folder(folder).data_cache.close()

    assert analysed == ["shop.robot.md"]
    assert problems == {"shop.robot.md": ["KeywordNotFound"]}
