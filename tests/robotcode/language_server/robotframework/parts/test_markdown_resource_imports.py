"""Tests for resource imports of Markdown files.

Robot Framework 7.5 accepts `.md` and `.markdown` resource files. RobotCode
accepts them the same way it accepts reStructuredText resources; extracting
the code blocks of such files is not covered here.
"""

from pathlib import Path
from typing import Callable, List

import pytest
from robot.errors import DataError

from robotcode.core.lsp.types import Diagnostic
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.robot.diagnostics.library_doc import (
    complete_resource_import,
    get_robot_library_html_doc_str,
)
from robotcode.robot.utils import RF_VERSION

MARKDOWN_RESOURCE = """\
# Keywords

```robotframework
*** Keywords ***
Markdown Keyword
    No Operation
```
"""

SUITE = """\
*** Settings ***
Resource    keywords.md

*** Test Cases ***
First
    No Operation
"""


def _import_diagnostics(
    protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], tmp_path: Path
) -> List[Diagnostic]:
    (tmp_path / "keywords.md").write_text(MARKDOWN_RESOURCE, encoding="utf-8")
    suite = tmp_path / "suite.robot"
    suite.write_text(SUITE, encoding="utf-8")

    namespace = protocol.documents_cache.get_initialized_namespace(open_temp_document(suite))

    # diagnostics of the `Resource` import line
    return [d for d in namespace.diagnostics if d.range.start.line == 1]


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="Markdown resource files exist since RF 7.5")
def test_markdown_resource_import_is_accepted(
    protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], tmp_path: Path
) -> None:
    diagnostics = _import_diagnostics(protocol, open_temp_document, tmp_path)

    assert not [d for d in diagnostics if "Invalid resource file extension" in d.message]


@pytest.mark.skipif(RF_VERSION >= (7, 5), reason="Markdown resource files are valid since RF 7.5")
def test_markdown_resource_import_is_rejected_before_rf_75(
    protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], tmp_path: Path
) -> None:
    diagnostics = _import_diagnostics(protocol, open_temp_document, tmp_path)

    # the rest of the message lists the supported extensions in set order
    assert [d.message for d in diagnostics if d.message.startswith("Invalid resource file extension '.md'")]


def test_resource_path_completion_lists_markdown_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # `complete_resource_import` changes the working directory
    monkeypatch.chdir(tmp_path)
    (tmp_path / "keywords.md").write_text(MARKDOWN_RESOURCE, encoding="utf-8")
    (tmp_path / "more.markdown").write_text(MARKDOWN_RESOURCE, encoding="utf-8")
    (tmp_path / "other.resource").write_text("*** Keywords ***\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("no resource\n", encoding="utf-8")

    result = complete_resource_import("./", working_dir=str(tmp_path), base_dir=str(tmp_path))

    assert result is not None
    labels = {r.label for r in result}
    assert "other.resource" in labels
    assert "notes.txt" not in labels
    assert ("keywords.md" in labels) == (RF_VERSION >= (7, 5))
    assert ("more.markdown" in labels) == (RF_VERSION >= (7, 5))


def test_html_documentation_of_markdown_resource_reports_a_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    resource = tmp_path / "keywords.md"
    resource.write_text(MARKDOWN_RESOURCE, encoding="utf-8")

    with pytest.raises(DataError, match="Libdoc does not support Markdown resource files"):
        get_robot_library_html_doc_str(str(resource), None, working_dir=str(tmp_path), base_dir=str(tmp_path))
