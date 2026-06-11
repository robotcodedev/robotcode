"""Tests for `DocumentsCacheHelper` model caching.

`get_model` returns a model that is cached on (and shared across) the document,
while `get_uncached_model` must always return a fresh, independent model. The
Robocop formatter mutates the model in place, so it relies on the uncached
variant - otherwise the mutations corrupt the shared cached model and repeated
formatting becomes non-idempotent (see
https://github.com/robotcodedev/robotcode/issues/612).
"""

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
from robot.parsing.model.blocks import File

from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.robot.diagnostics.document_cache_helper import DocumentsCacheHelper

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
