"""Handlers that keep cached results in step with invalidated documents and namespaces.

Find References caches its results; they must be dropped when the cache of a
document or a namespace is invalidated. The document of an invalidated
namespace is analyzed again, open or closed. A namespace that is built again
gets the diagnostics of its document collected again when the document is
open in the editor.
"""

from pathlib import Path
from typing import Callable

from pytest_mock import MockerFixture

from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol


def test_an_invalidated_document_cache_clears_the_reference_cache(protocol: RobotLanguageServerProtocol) -> None:
    assert protocol.robot_references.document_did_change in protocol.documents.on_document_cache_invalidated


def test_an_invalidated_namespace_clears_the_reference_cache(protocol: RobotLanguageServerProtocol) -> None:
    assert protocol.robot_references.namespace_invalidated in protocol.documents_cache.namespace_invalidated


def test_an_initialized_namespace_refreshes_the_diagnostics(protocol: RobotLanguageServerProtocol) -> None:
    assert protocol.robot_diagnostics._on_namespace_initialized in protocol.documents_cache.namespace_initialized


def test_an_invalidated_namespace_gets_its_document_analyzed_again(protocol: RobotLanguageServerProtocol) -> None:
    assert protocol.robot_diagnostics._on_namespace_invalidated in protocol.documents_cache.namespace_invalidated


def test_a_built_namespace_refreshes_the_diagnostics_only_of_an_open_document(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    (tmp_path / "suite.robot").write_text("*** Test Cases ***\nFirst\n    Log    hello\n", encoding="utf-8")
    document = open_temp_document(tmp_path / "suite.robot")
    namespace = protocol.documents_cache.get_namespace(document)
    run_as_task = mocker.patch("robotcode.language_server.robotframework.parts.diagnostics.run_as_task")

    protocol.robot_diagnostics._on_namespace_initialized(None, namespace)

    run_as_task.assert_not_called()

    document.opened_in_editor = True
    try:
        protocol.robot_diagnostics._on_namespace_initialized(None, namespace)
    finally:
        document.opened_in_editor = False

    run_as_task.assert_called_once_with(protocol.diagnostics.force_refresh_document, document)
