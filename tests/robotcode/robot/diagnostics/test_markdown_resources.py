"""Tests that an imported Markdown resource is read like Robot Framework reads it, from its code blocks."""

from pathlib import Path
from typing import Any, Iterator

import pytest
from robot.utils import FileReader

from robotcode.core.filewatcher import FileWatcherManagerDummy
from robotcode.core.uri import Uri
from robotcode.core.workspace import Workspace, WorkspaceFolder
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.document_cache_helper import DocumentsCacheHelper
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from tests.robotcode.language_server.robotframework.tools import write_project

pytestmark = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")

KEYWORDS = """\
# Keywords

```robot
*** Keywords ***
Wave
    Log    Bye
```

Some notes

- Greeting, in a block that continues the keyword section:

    ```robotframework
    Greet
        Log    Hello
    ```
"""

SUITE = """\
*** Settings ***
Resource    keywords.md

*** Test Cases ***
First
    Greet
"""


@pytest.fixture
def suite_namespace(tmp_path: Path) -> Iterator[Namespace]:
    write_project(tmp_path, {"keywords.md": KEYWORDS, "suite.robot": SUITE})

    workspace = Workspace(Uri.from_path(tmp_path), [WorkspaceFolder(tmp_path.name, Uri.from_path(tmp_path))])

    def read_text(sender: Any, uri: Uri) -> str:
        with FileReader(uri.to_path()) as reader:
            return str(reader.read())

    workspace.documents.on_read_document_text.add(read_text)
    # no `extensions`: Robot Framework reads an imported Markdown resource from its code blocks anyway
    helper = DocumentsCacheHelper(workspace, workspace.documents, FileWatcherManagerDummy(), RobotBaseProfile(), None)

    yield helper.get_namespace(workspace.documents.get_or_open_document(tmp_path / "suite.robot"))

    helper.get_imports_manager_for_workspace_folder(workspace.workspace_folders[0]).data_cache.close()


def test_a_keyword_of_a_markdown_resource_is_found_at_its_file_line(suite_namespace: Namespace, tmp_path: Path) -> None:
    keyword = suite_namespace.find_keyword("Greet")

    assert suite_namespace.diagnostics == []
    assert keyword is not None
    assert keyword.name_token is not None
    assert (Path(str(keyword.source)), keyword.line_no, keyword.name_token.col_offset) == (
        tmp_path / "keywords.md",
        14,
        4,
    )


def test_the_prose_and_fences_of_a_markdown_resource_are_no_keywords(suite_namespace: Namespace) -> None:
    resource = suite_namespace.get_imported_resource_libdoc("keywords.md")

    assert resource is not None
    assert sorted(k.name for k in resource.keywords.values()) == ["Greet", "Wave"]
