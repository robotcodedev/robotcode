"""Handlers that keep cached results in step with invalidated documents and namespaces.

Find References caches its results; they must be dropped when the cache of a
document or a namespace is invalidated. A namespace that is built again must
get the diagnostics of its document collected again.
"""

from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol


def test_an_invalidated_document_cache_clears_the_reference_cache(protocol: RobotLanguageServerProtocol) -> None:
    assert protocol.robot_references.document_did_change in protocol.documents.on_document_cache_invalidated


def test_an_invalidated_namespace_clears_the_reference_cache(protocol: RobotLanguageServerProtocol) -> None:
    assert protocol.robot_references.namespace_invalidated in protocol.documents_cache.namespace_invalidated


def test_an_initialized_namespace_refreshes_the_diagnostics(protocol: RobotLanguageServerProtocol) -> None:
    assert protocol.robot_diagnostics._on_namespace_initialized in protocol.documents_cache.namespace_initialized
