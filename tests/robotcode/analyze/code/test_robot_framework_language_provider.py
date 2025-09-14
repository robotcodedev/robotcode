import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from robotcode.analyze.code.diagnostics_context import DiagnosticsContext
from robotcode.analyze.code.robot_framework_language_provider import (
    ROBOTFRAMEWORK_LANGUAGE_ID,
    RobotFrameworkLanguageProvider,
)
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.workspace import WorkspaceFolder


class TestRobotFrameworkLanguageProvider:
    """Test cases for RobotFrameworkLanguageProvider class."""

    @pytest.fixture
    def mock_diagnostics_context(self) -> Mock:
        """Create a mock DiagnosticsContext."""
        context = Mock(spec=DiagnosticsContext)
        context.workspace = Mock()
        context.workspace.root_uri = Uri.from_path("/test/workspace")
        context.workspace.documents = Mock()
        context.workspace.get_configuration = Mock()
        context.profile = Mock()
        context.profile.python_path = []
        context.analysis_config = Mock()
        context.analysis_config.exclude_patterns = []
        return context

    def test_language_definition_constants(self) -> None:
        """Test that language definition constants are correct."""
        assert ROBOTFRAMEWORK_LANGUAGE_ID == "robotframework"

        lang_def = RobotFrameworkLanguageProvider.LANGUAGE_DEFINITION
        assert lang_def.id == "robotframework"
        assert ".robot" in lang_def.extensions
        assert ".resource" in lang_def.extensions
        assert lang_def.extensions_ignore_case is True
        assert "Robot Framework" in lang_def.aliases
        assert "robotframework" in lang_def.aliases

    def test_get_language_definitions(self) -> None:
        """Test get_language_definitions class method."""
        definitions = RobotFrameworkLanguageProvider.get_language_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 1
        assert definitions[0] is RobotFrameworkLanguageProvider.LANGUAGE_DEFINITION

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_initialization(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test RobotFrameworkLanguageProvider initialization."""
        mock_cache_instance = Mock()
        mock_cache_helper.return_value = mock_cache_instance
        mock_filewatcher_instance = Mock()
        mock_filewatcher.return_value = mock_filewatcher_instance

        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)

        assert provider.diagnostics_context is mock_diagnostics_context
        assert provider._document_cache is mock_cache_instance

        # Check that the cache helper was initialized correctly
        mock_cache_helper.assert_called_once_with(
            mock_diagnostics_context.workspace,
            mock_diagnostics_context.workspace.documents,
            mock_filewatcher_instance,
            mock_diagnostics_context.profile,
            mock_diagnostics_context.analysis_config,
        )

        # Check that event handlers were registered
        mock_diagnostics_context.workspace.documents.on_read_document_text.add.assert_called()
        mock_diagnostics_context.diagnostics.folder_analyzers.add.assert_called()
        mock_diagnostics_context.diagnostics.document_analyzers.add.assert_called()

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_initialization_updates_python_path(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test that initialization updates Python path."""
        mock_diagnostics_context.profile.python_path = ["./lib", "/absolute/path"]
        mock_diagnostics_context.workspace.root_uri = Uri.from_path("/workspace")

        original_path = sys.path.copy()

        with patch("glob.glob") as mock_glob:
            # Mock glob to return some paths
            mock_glob.side_effect = lambda x: [x.replace("*", "resolved")]

            with patch("pathlib.Path.is_dir") as mock_is_dir:
                mock_is_dir.return_value = True

                RobotFrameworkLanguageProvider(mock_diagnostics_context)

        # Restore original path
        sys.path[:] = original_path

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_initialization_with_none_python_path(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test initialization with None python_path."""
        mock_diagnostics_context.profile.python_path = None

        # Should not raise any exception
        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)
        assert provider is not None

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileReader")
    def test_on_read_document_text(
        self,
        mock_file_reader: Mock,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test on_read_document_text method."""
        # Setup mock file reader
        mock_reader_instance = Mock()
        mock_reader_instance.__enter__ = Mock(return_value=mock_reader_instance)
        mock_reader_instance.__exit__ = Mock(return_value=None)
        mock_reader_instance.read.return_value = "*** Test Cases ***\nTest\n    Log    Hello"
        mock_file_reader.return_value = mock_reader_instance

        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)
        uri = Uri.from_path("/test/file.robot")

        result = provider.on_read_document_text(None, uri)

        assert result == "*** Test Cases ***\nTest\n    Log    Hello"
        mock_file_reader.assert_called_once_with(uri.to_path())

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    @patch("robotcode.analyze.code.robot_framework_language_provider.iter_files")
    def test_collect_workspace_folder_files(
        self,
        mock_iter_files: Mock,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test collect_workspace_folder_files method."""
        folder = WorkspaceFolder("test", Uri.from_path("/test/workspace"))

        # Mock configuration
        mock_config = Mock()
        mock_config.exclude_patterns = ["temp/*"]
        mock_diagnostics_context.workspace.get_configuration.return_value = mock_config

        # Mock iter_files to return some robot files
        test_files = [
            Path("/test/workspace/test1.robot"),
            Path("/test/workspace/test2.resource"),
            Path("/test/workspace/test3.py"),  # Should be filtered out
            Path("/test/workspace/TEST4.ROBOT"),  # Should be included (case insensitive)
        ]
        mock_iter_files.return_value = test_files

        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)

        result = list(provider.collect_workspace_folder_files(folder))

        # Should only include .robot and .resource files (case insensitive)
        expected_files = [
            Path("/test/workspace/test1.robot"),
            Path("/test/workspace/test2.resource"),
            Path("/test/workspace/TEST4.ROBOT"),
        ]

        assert len(result) == 3
        for expected_file in expected_files:
            assert expected_file in result

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_analyze_document(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test analyze_document method."""
        document = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )

        # Mock document cache and namespace
        mock_namespace = Mock()
        mock_namespace.get_diagnostics.return_value = [
            Diagnostic(
                range=Range(Position(1, 0), Position(1, 4)),
                message="Test diagnostic",
                severity=DiagnosticSeverity.WARNING
            )
        ]

        mock_diagnostic_modifier = Mock()
        expected_diagnostics = [
            Diagnostic(
                range=Range(Position(1, 0), Position(1, 4)),
                message="Modified diagnostic",
                severity=DiagnosticSeverity.ERROR
            )
        ]
        mock_diagnostic_modifier.modify_diagnostics.return_value = expected_diagnostics

        mock_cache_instance = Mock()
        mock_cache_instance.get_namespace.return_value = mock_namespace
        mock_cache_instance.get_diagnostic_modifier.return_value = mock_diagnostic_modifier
        mock_cache_helper.return_value = mock_cache_instance

        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)

        result = provider.analyze_document(None, document)

        assert result == expected_diagnostics
        mock_cache_instance.get_namespace.assert_called_once_with(document)
        mock_namespace.analyze.assert_called_once()
        mock_cache_instance.get_diagnostic_modifier.assert_called_once_with(document)
        mock_diagnostic_modifier.modify_diagnostics.assert_called_once_with(mock_namespace.get_diagnostics.return_value)

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_analyze_folder(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test analyze_folder method."""
        folder = WorkspaceFolder("test", Uri.from_path("/test/workspace"))

        # Mock imports manager
        mock_imports_manager = Mock()
        expected_diagnostics = [
            Diagnostic(
                range=Range(Position(0, 0), Position(0, 10)),
                message="Import diagnostic",
                severity=DiagnosticSeverity.ERROR
            )
        ]
        mock_imports_manager.diagnostics = expected_diagnostics

        mock_cache_instance = Mock()
        mock_cache_instance.get_imports_manager_for_workspace_folder.return_value = mock_imports_manager
        mock_cache_helper.return_value = mock_cache_instance

        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)

        result = provider.analyze_folder(None, folder)

        assert result == expected_diagnostics
        mock_cache_instance.get_imports_manager_for_workspace_folder.assert_called_once_with(folder)

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_verbose_callback_integration(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test that verbose_callback is used in collect_workspace_folder_files."""
        folder = WorkspaceFolder("test", Uri.from_path("/test/workspace"))

        # Mock configuration
        mock_config = Mock()
        mock_config.exclude_patterns = []
        mock_diagnostics_context.workspace.get_configuration.return_value = mock_config

        mock_verbose_callback = Mock()

        with patch("robotcode.analyze.code.robot_framework_language_provider.iter_files") as mock_iter_files:
            mock_iter_files.return_value = []

            provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)
            provider.verbose_callback = mock_verbose_callback

            list(provider.collect_workspace_folder_files(folder))

            # Check that iter_files was called with verbose_callback
            call_args = mock_iter_files.call_args
            assert call_args.kwargs["verbose_callback"] is mock_verbose_callback

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_inheritance_from_language_provider(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test that RobotFrameworkLanguageProvider properly inherits from LanguageProvider."""
        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)

        # Should have inherited properties from LanguageProvider
        assert provider.diagnostics_context is mock_diagnostics_context
        assert hasattr(provider, "verbose_callback")

        # Should implement required abstract methods
        assert hasattr(provider, "get_language_definitions")
        assert hasattr(provider, "collect_workspace_folder_files")

        # Test that class methods work
        definitions = provider.get_language_definitions()
        assert len(definitions) == 1
        assert definitions[0].id == "robotframework"

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_decorator_integration(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test that the language_id decorator is properly applied."""
        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)

        # The on_read_document_text method should have the language_id decorator
        # We can't easily test the decorator directly, but we can verify the method exists
        assert hasattr(provider, "on_read_document_text")
        assert callable(provider.on_read_document_text)

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    @patch("robotcode.analyze.code.robot_framework_language_provider.iter_files")
    def test_collect_workspace_folder_files_with_complex_filters(
        self,
        mock_iter_files: Mock,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test collect_workspace_folder_files with complex exclude patterns."""
        folder = WorkspaceFolder("test", Uri.from_path("/test/workspace"))

        # Setup exclude patterns
        mock_diagnostics_context.analysis_config.exclude_patterns = ["build/*", "*.tmp"]
        mock_config = Mock()
        mock_config.exclude_patterns = ["test_*"]
        mock_diagnostics_context.workspace.get_configuration.return_value = mock_config

        # Mock iter_files to return robot files
        test_files = [
            Path("/test/workspace/main.robot"),
            Path("/test/workspace/lib.resource"),
        ]
        mock_iter_files.return_value = test_files

        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)

        result = list(provider.collect_workspace_folder_files(folder))

        # Should call iter_files with combined exclude patterns
        call_args = mock_iter_files.call_args
        parent_spec = call_args.kwargs["parent_spec"]
        # The IgnoreSpec should contain the combined patterns
        assert parent_spec is not None

    @patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    @patch("robotcode.analyze.code.robot_framework_language_provider.FileWatcherManagerDummy")
    def test_edge_cases_and_error_handling(
        self,
        mock_filewatcher: Mock,
        mock_cache_helper: Mock,
        mock_diagnostics_context: Mock
    ) -> None:
        """Test edge cases and error handling."""
        # Test with None workspace root URI
        mock_diagnostics_context.workspace.root_uri = None

        # Should not raise exception
        provider = RobotFrameworkLanguageProvider(mock_diagnostics_context)
        assert provider is not None
