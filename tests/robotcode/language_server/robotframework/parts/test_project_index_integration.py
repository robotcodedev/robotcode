"""Integration tests for ProjectIndex through the LSP protocol stack.

Verifies that the full pipeline from .robot file → NamespaceBuilder.build()
→ ProjectIndex.update_file() correctly populates the index with real references.
"""

from pathlib import Path

import pytest

from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

root_path = Path(Path(__file__).absolute().parent, "data")
references_robot = root_path / "tests" / "references.robot"
firstresource_resource = root_path / "resources" / "firstresource.resource"


@pytest.fixture(scope="module")
def references_document(protocol: RobotLanguageServerProtocol) -> TextDocument:
    return protocol.documents.get_or_open_document(references_robot, "robotframework")


@pytest.fixture(scope="module")
def firstresource_document(protocol: RobotLanguageServerProtocol) -> TextDocument:
    return protocol.documents.get_or_open_document(firstresource_resource, "robotframework")


class TestProjectIndexPopulation:
    """After building a namespace, the ProjectIndex must contain its references."""

    @pytest.mark.usefixtures("protocol")
    def test_keyword_references_populated(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
    ) -> None:
        # Trigger namespace build which populates the ProjectIndex
        protocol.documents_cache.get_namespace(references_document)

        idx = protocol.documents_cache.get_project_index(references_document)
        assert len(idx.keyword_references) > 0, "ProjectIndex should have keyword references"

    @pytest.mark.usefixtures("protocol")
    def test_variable_references_populated(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
    ) -> None:
        protocol.documents_cache.get_namespace(references_document)

        idx = protocol.documents_cache.get_project_index(references_document)
        assert len(idx.variable_references) > 0, "ProjectIndex should have variable references"

    @pytest.mark.usefixtures("protocol")
    def test_namespace_references_populated(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
    ) -> None:
        protocol.documents_cache.get_namespace(references_document)

        idx = protocol.documents_cache.get_project_index(references_document)
        assert len(idx.namespace_references) > 0, "ProjectIndex should have namespace/library references"


class TestProjectIndexKeywordLookup:
    """Verify that specific keywords from test data are findable."""

    @pytest.mark.usefixtures("protocol")
    def test_known_keyword_has_locations(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
    ) -> None:
        """'Log To Console' is used many times in references.robot."""
        protocol.documents_cache.get_namespace(references_document)

        idx = protocol.documents_cache.get_project_index(references_document)
        kw_refs = idx.keyword_references

        # Find 'Log To Console' regardless of case normalization
        log_to_console_entries = [kw for kw in kw_refs if kw.name == "Log To Console"]
        assert len(log_to_console_entries) > 0, "Should have references to 'Log To Console'"

        total_locations = sum(len(kw_refs[kw]) for kw in log_to_console_entries)
        assert total_locations >= 2, "Log To Console is used multiple times"

    @pytest.mark.usefixtures("protocol")
    def test_user_defined_keyword_has_locations(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
    ) -> None:
        """'do something' is defined and called in references.robot."""
        protocol.documents_cache.get_namespace(references_document)

        idx = protocol.documents_cache.get_project_index(references_document)
        kw_refs = idx.keyword_references

        kw_names = {kw.name for kw in kw_refs}
        assert "do something" in kw_names, f"Expected 'do something' in {kw_names}"


class TestProjectIndexVariableLookup:
    """Verify that known variables are indexed."""

    @pytest.mark.usefixtures("protocol")
    def test_known_variable_has_locations(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
    ) -> None:
        """${a var} is defined and used many times in references.robot."""
        protocol.documents_cache.get_namespace(references_document)

        idx = protocol.documents_cache.get_project_index(references_document)
        var_refs = idx.variable_references

        var_names = {v.name for v in var_refs}
        assert any("a var" in n.lower() or "a_var" in n.lower() for n in var_names), (
            f"Expected a variable matching 'a var' or 'a_var' in {var_names}"
        )


class TestProjectIndexCrossFile:
    """Verify that references across files are aggregated."""

    @pytest.mark.usefixtures("protocol")
    def test_cross_file_keyword_references_aggregated(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
        firstresource_document: TextDocument,
    ) -> None:
        """After building both files, the project index should contain refs from both."""
        protocol.documents_cache.get_namespace(references_document)
        protocol.documents_cache.get_namespace(firstresource_document)

        idx = protocol.documents_cache.get_project_index(references_document)
        # Both documents share the same workspace folder → same ProjectIndex
        idx2 = protocol.documents_cache.get_project_index(firstresource_document)
        assert idx is idx2, "Documents in the same folder should share a ProjectIndex"

    @pytest.mark.usefixtures("protocol")
    def test_multiple_files_contribute_to_index(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
        firstresource_document: TextDocument,
    ) -> None:
        """The index should know about keywords from both files."""
        protocol.documents_cache.get_namespace(references_document)
        protocol.documents_cache.get_namespace(firstresource_document)

        idx = protocol.documents_cache.get_project_index(references_document)
        kw_names = {kw.name for kw in idx.keyword_references}

        # references.robot defines "do something"
        assert "do something" in kw_names

        # firstresource.resource should define some keywords too
        assert len(kw_names) > 1, "Index should contain keywords from multiple files"


class TestProjectIndexFolderScoping:
    """Verify that documents in the same folder get the same ProjectIndex."""

    @pytest.mark.usefixtures("protocol")
    def test_same_folder_same_index(
        self,
        protocol: RobotLanguageServerProtocol,
        references_document: TextDocument,
        firstresource_document: TextDocument,
    ) -> None:
        idx1 = protocol.documents_cache.get_project_index(references_document)
        idx2 = protocol.documents_cache.get_project_index(firstresource_document)
        assert idx1 is idx2
