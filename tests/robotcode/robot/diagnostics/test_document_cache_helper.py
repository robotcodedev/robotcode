"""Tests for `DocumentsCacheHelper` model caching.

`get_model` returns a model that is cached on (and shared across) the document,
while `get_uncached_model` must always return a fresh, independent model. The
Robocop formatter mutates the model in place, so it relies on the uncached
variant - otherwise the mutations corrupt the shared cached model and repeated
formatting becomes non-idempotent (see
https://github.com/robotcodedev/robotcode/issues/612).

The helper also decides where `robotcode analyze code` keeps its cache.
"""

from pathlib import Path
from typing import Optional, cast
from unittest.mock import MagicMock

import pytest
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import File

from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.document_cache_helper import DocumentsCacheHelper
from robotcode.robot.diagnostics.namespace import DocumentType
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig
from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from robotcode.robot.language_definitions import MARKDOWN_LANGUAGE_ID
from robotcode.robot.utils.markdown_blocks import RobotBlock

TEXT = '*** Test Cases ***\nTest\n    Embedded "args"\n\n\n*** Keywords ***\nEmbedded "${args}"\n    No Operation\n'


@pytest.fixture
def cache_helper() -> DocumentsCacheHelper:
    workspace = MagicMock()
    workspace.get_workspace_folder.return_value = None
    return DocumentsCacheHelper(
        workspace=workspace,
        documents_manager=MagicMock(),
        file_watcher_manager=MagicMock(),
        robot_profile=None,
        analysis_config=None,
    )


def _document(tmp_path: Path, name: str = "test.robot") -> TextDocument:
    return TextDocument(
        document_uri=str(Uri.from_path(tmp_path / name).normalized()),
        language_id="robotframework",
        version=1,
        text=TEXT,
    )


def test_get_model_is_cached_on_the_document(cache_helper: DocumentsCacheHelper, tmp_path: Path) -> None:
    document = _document(tmp_path)

    assert cache_helper.get_model(document) is cache_helper.get_model(document)


@pytest.mark.parametrize("name", ["test.robot", "test.resource", "__init__.robot"])
def test_get_uncached_model_returns_a_fresh_model_every_time(
    cache_helper: DocumentsCacheHelper, tmp_path: Path, name: str
) -> None:
    document = _document(tmp_path, name)

    first = cache_helper.get_uncached_model(document)
    second = cache_helper.get_uncached_model(document)

    assert isinstance(first, File)
    assert first is not second
    assert first is not cache_helper.get_model(document)


def test_uncached_model_mutation_does_not_corrupt_the_cached_model(
    cache_helper: DocumentsCacheHelper,
    tmp_path: Path,
) -> None:
    document = _document(tmp_path)

    cached = cast(File, cache_helper.get_model(document))
    sections_before = len(cached.sections)

    uncached = cast(File, cache_helper.get_uncached_model(document))
    uncached.sections.clear()

    assert len(cached.sections) == sections_before
    assert cache_helper.get_model(document) is cached


# ---------------------------------------------------------------------------
# Namespace disk-cache keying and save gating
# ---------------------------------------------------------------------------


def test_namespace_cache_key_distinguishes_document_types(tmp_path: Path) -> None:
    from robotcode.robot.diagnostics.document_cache_helper import _namespace_cache_key
    from robotcode.robot.diagnostics.namespace import DocumentType

    source = str(tmp_path / "common.robot")

    keys = {
        _namespace_cache_key(source, DocumentType.GENERAL),
        _namespace_cache_key(source, DocumentType.RESOURCE),
        _namespace_cache_key(source, DocumentType.INIT),
        _namespace_cache_key(source, None),
    }

    assert len(keys) == 4
    assert all(key.startswith(source + "\n") for key in keys)


def _saved_document(tmp_path: Path, disk_info: object) -> TextDocument:
    return TextDocument(
        document_uri=str(Uri.from_path(tmp_path / "test.robot").normalized()),
        language_id="robotframework",
        version=None,
        text=TEXT,
        disk_info=disk_info,  # type: ignore[arg-type]
    )


def test_save_namespace_skips_when_meta_is_not_trustworthy(cache_helper: DocumentsCacheHelper, tmp_path: Path) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.namespace import DocumentType

    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    imports_manager.build_namespace_meta.return_value = None

    cache_helper._save_namespace_to_cache(
        str(tmp_path / "test.robot"), document, DocumentType.GENERAL, MagicMock(), imports_manager, disk_info, False
    )

    imports_manager.data_cache.save_entry.assert_not_called()


def test_save_namespace_skips_when_document_changed_during_save(
    cache_helper: DocumentsCacheHelper, tmp_path: Path
) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.namespace import DocumentType

    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    namespace = MagicMock()

    def mutate_and_serialize() -> object:
        document.apply_full_change(None, "changed")
        return MagicMock()

    namespace.to_data.side_effect = mutate_and_serialize

    cache_helper._save_namespace_to_cache(
        str(tmp_path / "test.robot"), document, DocumentType.GENERAL, namespace, imports_manager, disk_info, False
    )

    imports_manager.data_cache.save_entry.assert_not_called()


def test_save_namespace_skips_when_document_opened_during_save(
    cache_helper: DocumentsCacheHelper, tmp_path: Path
) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.namespace import DocumentType

    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    namespace = MagicMock()

    def open_and_serialize() -> object:
        document.version = 1
        return MagicMock()

    namespace.to_data.side_effect = open_and_serialize

    cache_helper._save_namespace_to_cache(
        str(tmp_path / "test.robot"), document, DocumentType.GENERAL, namespace, imports_manager, disk_info, False
    )

    imports_manager.data_cache.save_entry.assert_not_called()


def test_save_namespace_writes_type_keyed_entry(cache_helper: DocumentsCacheHelper, tmp_path: Path) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.document_cache_helper import _namespace_cache_key
    from robotcode.robot.diagnostics.namespace import DocumentType

    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    source = str(tmp_path / "test.robot")

    cache_helper._save_namespace_to_cache(
        source, document, DocumentType.RESOURCE, MagicMock(), imports_manager, disk_info, False
    )

    save_args = imports_manager.data_cache.save_entry.call_args[0]
    assert save_args[1] == _namespace_cache_key(source, DocumentType.RESOURCE)
    assert save_args[2] is imports_manager.build_namespace_meta.return_value


def test_try_load_reads_type_keyed_entry(cache_helper: DocumentsCacheHelper, tmp_path: Path) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.document_cache_helper import _namespace_cache_key
    from robotcode.robot.diagnostics.namespace import DocumentType

    source_file = tmp_path / "test.robot"
    source_file.write_text(TEXT)
    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    imports_manager.data_cache.read_entry.return_value = None

    result = cache_helper._try_load_cached_namespace(
        str(source_file), document, DocumentType.RESOURCE, imports_manager, False, disk_info
    )

    assert result is None
    read_args = imports_manager.data_cache.read_entry.call_args[0]
    assert read_args[1] == _namespace_cache_key(str(source_file), DocumentType.RESOURCE)


def _cache_helper_with(cache_dir: Optional[str]) -> DocumentsCacheHelper:
    return DocumentsCacheHelper(
        workspace=MagicMock(),
        documents_manager=MagicMock(),
        file_watcher_manager=MagicMock(),
        robot_profile=None,
        analysis_config=WorkspaceAnalysisConfig(cache_dir=cache_dir),
    )


@pytest.mark.parametrize(
    ("cache_dir", "expected"),
    [pytest.param(None, ".", id="no-cache-dir"), pytest.param("mycache", "mycache", id="relative-cache-dir")],
)
def test_cache_path_follows_the_cache_dir_of_the_robot_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cache_dir: Optional[str], expected: str
) -> None:
    monkeypatch.delenv("ROBOTCODE_CACHE_DIR", raising=False)
    folder = Uri.from_path(tmp_path)

    assert _cache_helper_with(cache_dir).calc_cache_path(folder) == folder.to_path() / expected


def test_cache_path_takes_an_absolute_cache_dir_as_it_is(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ROBOTCODE_CACHE_DIR", raising=False)
    cache_dir = tmp_path / "elsewhere"

    assert _cache_helper_with(str(cache_dir)).calc_cache_path(Uri.from_path(tmp_path / "project")) == cache_dir


def test_robotcode_cache_dir_wins_over_the_cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROBOTCODE_CACHE_DIR", str(tmp_path / "env"))

    assert _cache_helper_with("mycache").calc_cache_path(Uri.from_path(tmp_path)) == tmp_path / "env"


requires_markdown = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")

MARKDOWN_SUITE = """\
# Shop
*** Test Cases ***
Some prose that looks like a section.

```robot
*** Settings ***
Documentation    The shop.
```

1. A list item with a test:

    ```robotframework
    *** Test Cases ***
    Indented Test
        Log    one
    ```
"""


def _markdown_helper() -> DocumentsCacheHelper:
    workspace = MagicMock()
    workspace.get_workspace_folder.return_value = None
    return DocumentsCacheHelper(
        workspace=workspace,
        documents_manager=MagicMock(),
        file_watcher_manager=MagicMock(),
        robot_profile=RobotBaseProfile(extensions="robot:md"),
        analysis_config=None,
    )


def _markdown_document(
    tmp_path: Path, name: str, text: str = MARKDOWN_SUITE, language_id: str = MARKDOWN_LANGUAGE_ID
) -> TextDocument:
    return TextDocument(
        document_uri=str(Uri.from_path(tmp_path / name).normalized()),
        language_id=language_id,
        version=1,
        text=text,
    )


@requires_markdown
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("__init__.md", DocumentType.INIT),
        ("__init__.markdown", DocumentType.INIT),
        ("shop.robot.md", DocumentType.GENERAL),
        ("__init__.robot.md", DocumentType.GENERAL),
    ],
)
def test_markdown_documents_are_typed_by_their_name(tmp_path: Path, name: str, expected: DocumentType) -> None:
    assert _markdown_helper().get_document_type(_markdown_document(tmp_path, name)) == expected


@requires_markdown
def test_a_markdown_file_of_another_language_is_no_robot_document(tmp_path: Path) -> None:
    document = _markdown_document(tmp_path, "shop.robot.md", language_id="markdown")

    assert _markdown_helper().get_document_type(document) == DocumentType.UNKNOWN


@requires_markdown
def test_the_tokens_of_a_markdown_suite_have_the_positions_in_the_file(tmp_path: Path) -> None:
    helper = _markdown_helper()
    model = cast(File, helper.get_model(_markdown_document(tmp_path, "shop.robot.md")))

    # by name: pytest would take the classes `TestCase` and `TestCaseSection` of Robot Framework for test classes
    tests = [t for s in model.sections if type(s).__name__ == "TestCaseSection" for t in s.body if t.name]

    assert [(t.name, t.header.get_token(Token.TESTCASE_NAME).lineno, t.header.col_offset) for t in tests] == [
        ("Indented Test", 14, 4)
    ]
    assert [type(s).__name__ for s in model.sections if s.header is not None] == [
        "SettingSection",
        "TestCaseSection",
    ]


CONTINUED_TEST = """\
```robot
*** Test Cases ***
First Test
    Log    first step
```

The test goes on after this paragraph.

```robot
    Log    second step
```
"""


@requires_markdown
def test_a_block_continues_the_test_of_the_block_before(tmp_path: Path) -> None:
    model = cast(File, _markdown_helper().get_model(_markdown_document(tmp_path, "shop.robot.md", CONTINUED_TEST)))

    # by name: pytest would take the classes `TestCase` and `TestCaseSection` of Robot Framework for test classes
    tests = [t for s in model.sections if type(s).__name__ == "TestCaseSection" for t in s.body if t.name]

    assert [(t.name, [(k.args, k.lineno) for k in t.body if type(k).__name__ == "KeywordCall"]) for t in tests] == [
        ("First Test", [(("first step",), 4), (("second step",), 10)])
    ]


@requires_markdown
def test_the_blocks_of_a_markdown_document(tmp_path: Path) -> None:
    helper = _markdown_helper()

    assert helper.get_markdown_blocks(_markdown_document(tmp_path, "shop.robot.md")) == [
        RobotBlock(4, 7),
        RobotBlock(11, 15, 4),
    ]
