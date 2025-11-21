from typing import List, Optional
from unittest.mock import Mock

import pytest

from robotcode.analyze.code.diagnostics_context import DiagnosticHandlers, DiagnosticsContext
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.workspace import WorkspaceFolder


class TestDiagnosticHandlers:
    """Test cases for DiagnosticHandlers class."""

    def test_diagnostic_handlers_initialization(self) -> None:
        """Test DiagnosticHandlers initialization."""
        handlers = DiagnosticHandlers()
        assert handlers is not None
        assert hasattr(handlers, "document_analyzers")
        assert hasattr(handlers, "folder_analyzers")
        assert hasattr(handlers, "collectors")

    def test_analyze_folder_with_no_handlers(self) -> None:
        """Test analyze_folder with no registered handlers."""
        handlers = DiagnosticHandlers()
        folder = WorkspaceFolder("test", Uri.from_path("/test"))

        result = handlers.analyze_folder(folder)

        assert result == []

    def test_analyze_folder_with_handler_returning_diagnostics(self) -> None:
        """Test analyze_folder with handler returning diagnostics."""
        handlers = DiagnosticHandlers()
        folder = WorkspaceFolder("test", Uri.from_path("/test"))

        expected_diagnostics = [
            Diagnostic(
                range=Range(Position(0, 0), Position(0, 10)),
                message="Test diagnostic",
                severity=DiagnosticSeverity.ERROR
            )
        ]

        # Register a mock handler
        def mock_handler(sender, folder: WorkspaceFolder) -> Optional[List[Diagnostic]]:
            return expected_diagnostics

        handlers.folder_analyzers.add(mock_handler)

        result = handlers.analyze_folder(folder)

        assert len(result) == 1
        assert result[0] == expected_diagnostics

    def test_analyze_folder_with_handler_raising_exception(self) -> None:
        """Test analyze_folder with handler raising exception."""
        handlers = DiagnosticHandlers()
        folder = WorkspaceFolder("test", Uri.from_path("/test"))

        test_exception = ValueError("Test error")

        def mock_handler(sender, folder: WorkspaceFolder) -> Optional[List[Diagnostic]]:
            raise test_exception

        handlers.folder_analyzers.add(mock_handler)

        result = handlers.analyze_folder(folder)

        assert len(result) == 1
        assert isinstance(result[0], ValueError)
        assert str(result[0]) == "Test error"

    def test_analyze_folder_with_multiple_handlers(self) -> None:
        """Test analyze_folder with multiple handlers."""
        handlers = DiagnosticHandlers()
        folder = WorkspaceFolder("test", Uri.from_path("/test"))

        diagnostics1 = [Diagnostic(
            range=Range(Position(0, 0), Position(0, 10)),
            message="First diagnostic",
            severity=DiagnosticSeverity.ERROR
        )]

        diagnostics2 = [Diagnostic(
            range=Range(Position(1, 0), Position(1, 10)),
            message="Second diagnostic",
            severity=DiagnosticSeverity.WARNING
        )]

        def handler1(sender, folder: WorkspaceFolder) -> Optional[List[Diagnostic]]:
            return diagnostics1

        def handler2(sender, folder: WorkspaceFolder) -> Optional[List[Diagnostic]]:
            return diagnostics2

        handlers.folder_analyzers.add(handler1)
        handlers.folder_analyzers.add(handler2)

        result = handlers.analyze_folder(folder)

        assert len(result) == 2
        assert diagnostics1 in result
        assert diagnostics2 in result

    def test_analyze_document_with_no_handlers(self) -> None:
        """Test analyze_document with no registered handlers."""
        handlers = DiagnosticHandlers()
        document = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )

        result = handlers.analyze_document(document)

        assert result == []

    def test_analyze_document_with_handler_returning_diagnostics(self) -> None:
        """Test analyze_document with handler returning diagnostics."""
        handlers = DiagnosticHandlers()
        document = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )

        expected_diagnostics = [
            Diagnostic(
                range=Range(Position(1, 0), Position(1, 4)),
                message="Test diagnostic",
                severity=DiagnosticSeverity.WARNING
            )
        ]

        def mock_handler(sender, document: TextDocument) -> Optional[List[Diagnostic]]:
            return expected_diagnostics

        handlers.document_analyzers.add(mock_handler)

        result = handlers.analyze_document(document)

        assert len(result) == 1
        assert result[0] == expected_diagnostics

    def test_analyze_document_with_handler_raising_exception(self) -> None:
        """Test analyze_document with handler raising exception."""
        handlers = DiagnosticHandlers()
        document = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )

        test_exception = RuntimeError("Analysis error")

        def mock_handler(sender, document: TextDocument) -> Optional[List[Diagnostic]]:
            raise test_exception

        handlers.document_analyzers.add(mock_handler)

        result = handlers.analyze_document(document)

        assert len(result) == 1
        assert isinstance(result[0], RuntimeError)
        assert str(result[0]) == "Analysis error"

    def test_analyze_document_with_language_filter(self) -> None:
        """Test analyze_document with language filtering."""
        handlers = DiagnosticHandlers()

        # Create a Python document
        python_doc = TextDocument(
            document_uri="file:///test.py",
            language_id="python",
            version=1,
            text="print('hello')"
        )

        # Create a Robot Framework document
        robot_doc = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )

        diagnostics = [Diagnostic(
            range=Range(Position(0, 0), Position(0, 10)),
            message="Robot diagnostic",
            severity=DiagnosticSeverity.INFORMATION
        )]

        call_count = 0

        def robot_handler(sender, document: TextDocument) -> Optional[List[Diagnostic]]:
            nonlocal call_count
            call_count += 1
            # Only return diagnostics for robot files
            if document.language_id == "robotframework":
                return diagnostics
            return None

        handlers.document_analyzers.add(robot_handler)

        # Analyze Python document - should not trigger Robot handler
        python_result = handlers.analyze_document(python_doc)

        # Analyze Robot document - should trigger Robot handler
        robot_result = handlers.analyze_document(robot_doc)

        # Both documents are analyzed, but only robot returns diagnostics
        assert len(python_result) == 1
        assert python_result[0] is None
        assert len(robot_result) == 1
        assert robot_result[0] == diagnostics
        assert call_count == 2

    def test_collect_diagnostics_with_no_collectors(self) -> None:
        """Test collect_diagnostics with no registered collectors."""
        handlers = DiagnosticHandlers()
        document = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )

        result = handlers.collect_diagnostics(document)

        assert result == []

    def test_collect_diagnostics_with_collector_returning_diagnostics(self) -> None:
        """Test collect_diagnostics with collector returning diagnostics."""
        handlers = DiagnosticHandlers()
        document = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )

        expected_diagnostics = [
            Diagnostic(
                range=Range(Position(2, 4), Position(2, 7)),
                message="Collected diagnostic",
                severity=DiagnosticSeverity.HINT
            )
        ]

        def mock_collector(sender, document: TextDocument) -> Optional[List[Diagnostic]]:
            return expected_diagnostics

        handlers.collectors.add(mock_collector)

        result = handlers.collect_diagnostics(document)

        assert len(result) == 1
        assert result[0] == expected_diagnostics

    def test_collect_diagnostics_with_multiple_collectors(self) -> None:
        """Test collect_diagnostics with multiple collectors."""
        handlers = DiagnosticHandlers()
        document = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )

        diagnostics1 = [Diagnostic(
            range=Range(Position(0, 0), Position(0, 10)),
            message="First collected",
            severity=DiagnosticSeverity.HINT
        )]

        diagnostics2 = [Diagnostic(
            range=Range(Position(1, 0), Position(1, 10)),
            message="Second collected",
            severity=DiagnosticSeverity.INFORMATION
        )]

        def collector1(sender, document: TextDocument) -> Optional[List[Diagnostic]]:
            return diagnostics1

        def collector2(sender, document: TextDocument) -> Optional[List[Diagnostic]]:
            return diagnostics2

        handlers.collectors.add(collector1)
        handlers.collectors.add(collector2)

        result = handlers.collect_diagnostics(document)

        assert len(result) == 2
        assert diagnostics1 in result
        assert diagnostics2 in result

    def test_handlers_return_none(self) -> None:
        """Test handlers that return None."""
        handlers = DiagnosticHandlers()
        document = TextDocument(
            document_uri="file:///test.robot",
            language_id="robotframework",
            version=1,
            text="*** Test Cases ***\nTest\n    Log    Hello"
        )
        folder = WorkspaceFolder("test", Uri.from_path("/test"))

        def none_handler(sender, item) -> None:
            return None

        handlers.document_analyzers.add(none_handler)
        handlers.folder_analyzers.add(none_handler)
        handlers.collectors.add(none_handler)

        doc_result = handlers.analyze_document(document)
        folder_result = handlers.analyze_folder(folder)
        collect_result = handlers.collect_diagnostics(document)

        assert len(doc_result) == 1
        assert doc_result[0] is None
        assert len(folder_result) == 1
        assert folder_result[0] is None
        assert len(collect_result) == 1
        assert collect_result[0] is None


class TestDiagnosticsContext:
    """Test cases for DiagnosticsContext abstract base class."""

    def test_diagnostics_context_is_abstract(self) -> None:
        """Test that DiagnosticsContext cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DiagnosticsContext()  # type: ignore

    def test_concrete_implementation_must_implement_all_properties(self) -> None:
        """Test that concrete implementations must implement all abstract properties."""
        # Create a partial implementation missing some properties
        class PartialDiagnosticsContext(DiagnosticsContext):
            pass

        with pytest.raises(TypeError):
            PartialDiagnosticsContext()  # type: ignore

    def test_concrete_implementation_with_all_properties(self) -> None:
        """Test that concrete implementations with all properties work."""
        class ConcreteDiagnosticsContext(DiagnosticsContext):
            def __init__(self):
                self._analysis_config = Mock()
                self._profile = Mock()
                self._workspace = Mock()
                self._diagnostics = DiagnosticHandlers()

            @property
            def analysis_config(self):
                return self._analysis_config

            @property
            def profile(self):
                return self._profile

            @property
            def workspace(self):
                return self._workspace

            @property
            def diagnostics(self):
                return self._diagnostics

        # Should not raise any exception
        context = ConcreteDiagnosticsContext()
        assert context.analysis_config is not None
        assert context.profile is not None
        assert context.workspace is not None
        assert isinstance(context.diagnostics, DiagnosticHandlers)
