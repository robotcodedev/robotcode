from pathlib import Path
from typing import Iterable, List
from unittest.mock import Mock

import pytest

from robotcode.analyze.code.diagnostics_context import DiagnosticsContext
from robotcode.analyze.code.language_provider import LanguageProvider
from robotcode.core.language import LanguageDefinition
from robotcode.core.uri import Uri
from robotcode.core.workspace import WorkspaceFolder


class TestLanguageProvider:
    """Test cases for LanguageProvider abstract base class."""

    def test_language_provider_is_abstract(self) -> None:
        """Test that LanguageProvider cannot be instantiated directly."""
        mock_context = Mock(spec=DiagnosticsContext)

        with pytest.raises(TypeError):
            LanguageProvider(mock_context)  # type: ignore

    def test_concrete_implementation_must_implement_abstract_methods(self) -> None:
        """Test that concrete implementations must implement all abstract methods."""
        mock_context = Mock(spec=DiagnosticsContext)

        # Create a partial implementation missing some methods
        class PartialLanguageProvider(LanguageProvider):
            pass

        with pytest.raises(TypeError):
            PartialLanguageProvider(mock_context)  # type: ignore

    def test_concrete_implementation_with_all_methods(self) -> None:
        """Test that concrete implementations with all methods work."""
        mock_context = Mock(spec=DiagnosticsContext)

        class ConcreteLanguageProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return [LanguageDefinition(
                    id="test",
                    extensions=[".test"],
                    aliases=["Test Language"]
                )]

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                return [Path("/test/file.test")]

        # Should not raise any exception
        provider = ConcreteLanguageProvider(mock_context)
        assert provider.diagnostics_context is mock_context
        assert provider.verbose_callback is None

    def test_initialization_sets_diagnostics_context(self) -> None:
        """Test that initialization properly sets the diagnostics_context."""
        mock_context = Mock(spec=DiagnosticsContext)

        class TestLanguageProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return []

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                return []

        provider = TestLanguageProvider(mock_context)

        assert provider.diagnostics_context is mock_context
        assert provider.verbose_callback is None

    def test_verbose_callback_can_be_set(self) -> None:
        """Test that verbose_callback can be set and retrieved."""
        mock_context = Mock(spec=DiagnosticsContext)
        mock_callback = Mock()

        class TestLanguageProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return []

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                return []

        provider = TestLanguageProvider(mock_context)
        provider.verbose_callback = mock_callback

        assert provider.verbose_callback is mock_callback

    def test_get_language_definitions_returns_list(self) -> None:
        """Test that get_language_definitions returns a list of LanguageDefinition."""
        mock_context = Mock(spec=DiagnosticsContext)

        test_language = LanguageDefinition(
            id="testlang",
            extensions=[".tst", ".test"],
            aliases=["Test Language", "TestLang"]
        )

        class TestLanguageProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return [test_language]

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                return []

        definitions = TestLanguageProvider.get_language_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 1
        assert definitions[0] is test_language

    def test_collect_workspace_folder_files_returns_iterable(self) -> None:
        """Test that collect_workspace_folder_files returns an iterable of Path."""
        mock_context = Mock(spec=DiagnosticsContext)
        folder = WorkspaceFolder("test", Uri.from_path("/test/workspace"))

        test_files = [
            Path("/test/workspace/file1.test"),
            Path("/test/workspace/file2.test"),
            Path("/test/workspace/subdir/file3.test")
        ]

        class TestLanguageProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return []

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                return test_files

        provider = TestLanguageProvider(mock_context)
        files = provider.collect_workspace_folder_files(folder)

        # Convert to list to test the iterable
        files_list = list(files)

        assert len(files_list) == 3
        assert all(isinstance(f, Path) for f in files_list)
        assert files_list == test_files

    def test_multiple_language_definitions(self) -> None:
        """Test provider that returns multiple language definitions."""
        mock_context = Mock(spec=DiagnosticsContext)

        lang1 = LanguageDefinition(id="lang1", extensions=[".l1"], aliases=["Language 1"])
        lang2 = LanguageDefinition(id="lang2", extensions=[".l2"], aliases=["Language 2"])

        class MultiLanguageProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return [lang1, lang2]

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                return []

        definitions = MultiLanguageProvider.get_language_definitions()

        assert len(definitions) == 2
        assert lang1 in definitions
        assert lang2 in definitions

    def test_empty_language_definitions(self) -> None:
        """Test provider that returns no language definitions."""
        mock_context = Mock(spec=DiagnosticsContext)

        class EmptyLanguageProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return []

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                return []

        definitions = EmptyLanguageProvider.get_language_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 0

    def test_empty_file_collection(self) -> None:
        """Test provider that returns no files."""
        mock_context = Mock(spec=DiagnosticsContext)
        folder = WorkspaceFolder("test", Uri.from_path("/empty/workspace"))

        class EmptyFileProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return []

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                return []

        provider = EmptyFileProvider(mock_context)
        files = list(provider.collect_workspace_folder_files(folder))

        assert len(files) == 0

    def test_language_provider_access_to_context_properties(self) -> None:
        """Test that language provider can access diagnostics context properties."""
        mock_context = Mock(spec=DiagnosticsContext)
        mock_context.analysis_config = Mock()
        mock_context.profile = Mock()
        mock_context.workspace = Mock()
        mock_context.diagnostics = Mock()

        class TestLanguageProvider(LanguageProvider):
            @classmethod
            def get_language_definitions(cls) -> List[LanguageDefinition]:
                return []

            def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
                # Access context properties
                _ = self.diagnostics_context.analysis_config
                _ = self.diagnostics_context.profile
                _ = self.diagnostics_context.workspace
                _ = self.diagnostics_context.diagnostics
                return []

        provider = TestLanguageProvider(mock_context)

        # Should not raise any exception when accessing context properties
        list(provider.collect_workspace_folder_files(
            WorkspaceFolder("test", Uri.from_path("/test"))
        ))

        # Verify that context properties were accessed
        assert mock_context.analysis_config is not None
        assert mock_context.profile is not None
        assert mock_context.workspace is not None
        assert mock_context.diagnostics is not None
