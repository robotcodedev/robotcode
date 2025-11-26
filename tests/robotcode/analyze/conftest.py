from pathlib import Path
from unittest.mock import Mock

import pytest

from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.workspace import WorkspaceFolder
from robotcode.plugin import Application
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig


@pytest.fixture
def sample_robot_content() -> str:
    """Sample Robot Framework test content."""
    return """*** Settings ***
Library    Collections

*** Variables ***
${VAR}    Hello World

*** Test Cases ***
Sample Test
    [Documentation]    A sample test case
    Log    ${VAR}
    Should Be Equal    ${VAR}    Hello World

Another Test
    [Tags]    smoke
    Log    Another test
    Create List    item1    item2
    Log    Test completed
"""


@pytest.fixture
def sample_resource_content() -> str:
    """Sample Robot Framework resource content."""
    return """*** Settings ***
Library    BuiltIn

*** Variables ***
${RESOURCE_VAR}    Resource Value

*** Keywords ***
Custom Keyword
    [Documentation]    A custom keyword
    [Arguments]    ${arg}
    Log    Argument: ${arg}
    RETURN    ${arg}

Another Keyword
    Log    Resource keyword
"""


@pytest.fixture
def invalid_robot_content() -> str:
    """Invalid Robot Framework content with syntax errors."""
    return """*** Test Cases ***
Test With Syntax Error
    [Documentation]    Missing proper keyword call
    InvalidKeyword    # This keyword doesn't exist
    Log    # Missing argument
    Should Be Equal    only_one_arg    # Missing second argument

*** Keywords ***
Keyword With Error
    [Arguments]    ${arg1}    ${arg2
    # Malformed argument definition above
    Log    ${undefined_var}
"""


@pytest.fixture
def sample_diagnostics() -> list[Diagnostic]:
    """Sample diagnostic messages."""
    return [
        Diagnostic(
            range=Range(Position(0, 0), Position(0, 15)),
            message="Missing library import",
            severity=DiagnosticSeverity.ERROR,
            code="MissingLibrary"
        ),
        Diagnostic(
            range=Range(Position(3, 4), Position(3, 18)),
            message="Undefined keyword",
            severity=DiagnosticSeverity.ERROR,
            code="UndefinedKeyword"
        ),
        Diagnostic(
            range=Range(Position(5, 4), Position(5, 7)),
            message="Deprecated keyword usage",
            severity=DiagnosticSeverity.WARNING,
            code="DeprecatedKeyword"
        ),
        Diagnostic(
            range=Range(Position(7, 0), Position(7, 10)),
            message="Code style suggestion",
            severity=DiagnosticSeverity.INFORMATION,
            code="CodeStyle"
        ),
        Diagnostic(
            range=Range(Position(9, 4), Position(9, 15)),
            message="Performance hint",
            severity=DiagnosticSeverity.HINT,
            code="Performance"
        ),
    ]


@pytest.fixture
def mock_application() -> Mock:
    """Mock Application for testing."""
    app = Mock(spec=Application)
    app.config = Mock()
    app.config.verbose = False
    app.config.config_files = []
    app.config.root = None
    app.config.no_vcs = False
    app.config.profiles = []
    app.verbose = Mock()
    app.error = Mock()
    app.echo = Mock()
    app.exit = Mock()
    return app


@pytest.fixture
def mock_analysis_config() -> Mock:
    """Mock WorkspaceAnalysisConfig for testing."""
    config = Mock(spec=WorkspaceAnalysisConfig)
    config.exclude_patterns = []
    config.load_library_timeout = None
    return config


@pytest.fixture
def mock_robot_profile() -> Mock:
    """Mock RobotBaseProfile for testing."""
    profile = Mock(spec=RobotBaseProfile)
    profile.python_path = []
    profile.variables = {}
    profile.variable_files = []
    return profile


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace with sample files."""
    workspace_dir = tmp_path / "test_workspace"
    workspace_dir.mkdir()

    # Create main test file
    test_file = workspace_dir / "test_main.robot"
    test_file.write_text("""*** Settings ***
Library    Collections

*** Variables ***
${TEST_VAR}    Test Value

*** Test Cases ***
Main Test
    Log    ${TEST_VAR}
    Should Be Equal    ${TEST_VAR}    Test Value
""")

    # Create resource file
    resource_file = workspace_dir / "resources" / "common.resource"
    resource_file.parent.mkdir()
    resource_file.write_text("""*** Settings ***
Library    BuiltIn

*** Keywords ***
Common Keyword
    Log    Common functionality
""")

    # Create file with errors
    error_file = workspace_dir / "tests" / "error_test.robot"
    error_file.parent.mkdir()
    error_file.write_text("""*** Test Cases ***
Error Test
    NonExistentKeyword
    Log    # Missing argument
""")

    # Create Python file (should be ignored by robot analyzer)
    python_file = workspace_dir / "utils.py"
    python_file.write_text("print('Hello World')")

    # Create .robotignore file
    robotignore = workspace_dir / ".robotignore"
    robotignore.write_text("temp/\n*.tmp\n")

    # Create temp directory and file (should be ignored)
    temp_dir = workspace_dir / "temp"
    temp_dir.mkdir()
    temp_file = temp_dir / "temp_test.robot"
    temp_file.write_text("*** Test Cases ***\nTemp Test\n    Log    Should be ignored")

    return workspace_dir


@pytest.fixture
def sample_workspace_folder(temp_workspace: Path) -> WorkspaceFolder:
    """Create a WorkspaceFolder from the temp workspace."""
    return WorkspaceFolder("test_workspace", Uri.from_path(temp_workspace))


@pytest.fixture
def sample_text_document(sample_robot_content: str) -> TextDocument:
    """Create a sample TextDocument."""
    return TextDocument(
        document_uri="file:///test/sample.robot",
        language_id="robotframework",
        version=1,
        text=sample_robot_content
    )


@pytest.fixture
def error_text_document(invalid_robot_content: str) -> TextDocument:
    """Create a TextDocument with errors."""
    return TextDocument(
        document_uri="file:///test/error.robot",
        language_id="robotframework",
        version=1,
        text=invalid_robot_content
    )


@pytest.fixture
def resource_text_document(sample_resource_content: str) -> TextDocument:
    """Create a resource TextDocument."""
    return TextDocument(
        document_uri="file:///test/sample.resource",
        language_id="robotframework",
        version=1,
        text=sample_resource_content
    )


class SampleData:
    """Container for sample test data."""

    ROBOT_FILES = {
        "simple.robot": """*** Test Cases ***
Simple Test
    Log    Hello World
""",
        "with_keywords.robot": """*** Settings ***
Library    Collections

*** Keywords ***
Custom Keyword
    [Arguments]    ${arg}
    Log    ${arg}

*** Test Cases ***
Test With Keywords
    Custom Keyword    test_value
    Create List    1    2    3
""",
        "with_errors.robot": """*** Test Cases ***
Error Test
    UndefinedKeyword    # This should cause an error
    Log    # Missing required argument
    Should Be Equal    only_one    # Missing second argument
""",
        "resource.resource": """*** Keywords ***
Resource Keyword
    Log    From resource file
"""
    }

    EXPECTED_DIAGNOSTICS = {
        "error": Diagnostic(
            range=Range(Position(2, 4), Position(2, 20)),
            message="Undefined keyword 'UndefinedKeyword'",
            severity=DiagnosticSeverity.ERROR,
            code="UndefinedKeyword"
        ),
        "warning": Diagnostic(
            range=Range(Position(3, 4), Position(3, 7)),
            message="Missing required argument",
            severity=DiagnosticSeverity.WARNING,
            code="MissingArgument"
        ),
        "info": Diagnostic(
            range=Range(Position(1, 0), Position(1, 11)),
            message="Consider adding documentation",
            severity=DiagnosticSeverity.INFORMATION,
            code="MissingDocumentation"
        ),
        "hint": Diagnostic(
            range=Range(Position(4, 4), Position(4, 18)),
            message="Consider using built-in keyword",
            severity=DiagnosticSeverity.HINT,
            code="OptimizationHint"
        )
    }


@pytest.fixture
def sample_data() -> SampleData:
    """Provide sample test data."""
    return SampleData()
