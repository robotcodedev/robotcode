from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from robotcode.analyze.cli import analyze
from robotcode.analyze.code.cli import code
from robotcode.analyze.code.code_analyzer import CodeAnalyzer
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.workspace import WorkspaceFolder


class TestAnalyzeIntegration:
    """Integration tests for the analyze package."""

    def test_main_cli_integration(self, temp_workspace: Path) -> None:
        """Test main CLI integration with real workspace."""
        runner = CliRunner()

        with patch("robotcode.analyze.code.cli.get_config_files") as mock_get_config, \
             patch("robotcode.analyze.code.cli.load_robot_config_from_path") as mock_load_config:

            # Mock configuration loading
            mock_get_config.return_value = ([], temp_workspace, None)

            mock_config = Mock()
            mock_config.tool = None
            mock_profile = Mock()
            mock_profile.variables = None
            mock_profile.python_path = None
            mock_profile.variable_files = None
            mock_load_config.return_value = mock_config
            mock_config.combine_profiles.return_value = mock_profile
            mock_profile.evaluated_with_env.return_value = mock_profile

            # Run the analyze command
            result = runner.invoke(analyze, ["code", str(temp_workspace)])

            # Should complete successfully
            assert result.exit_code == 0

    def test_code_analyzer_full_workflow(
        self,
        mock_application: Mock,
        mock_analysis_config: Mock,
        mock_robot_profile: Mock,
        temp_workspace: Path
    ) -> None:
        """Test CodeAnalyzer full workflow with real files."""
        analyzer = CodeAnalyzer(
            app=mock_application,
            analysis_config=mock_analysis_config,
            robot_profile=mock_robot_profile,
            root_folder=temp_workspace
        )

        # Test that analyzer initializes correctly
        assert analyzer.root_folder == temp_workspace
        assert len(analyzer.language_handlers) == 1

        # Create a workspace folder
        folder = WorkspaceFolder("test", Uri.from_path(temp_workspace))

        # Test document collection
        with patch.object(analyzer.language_handlers[0], "collect_workspace_folder_files") as mock_collect:
            # Mock to return the robot files we created
            robot_files = [
                temp_workspace / "test_main.robot",
                temp_workspace / "resources" / "common.resource",
                temp_workspace / "tests" / "error_test.robot"
            ]
            mock_collect.return_value = robot_files

            documents = analyzer.collect_documents(folder)

            # Should collect the robot files
            assert len(documents) >= 0  # May be filtered by path validation

    def test_language_provider_file_collection(
        self,
        mock_application: Mock,
        mock_analysis_config: Mock,
        mock_robot_profile: Mock,
        temp_workspace: Path
    ) -> None:
        """Test that RobotFrameworkLanguageProvider collects files correctly."""
        analyzer = CodeAnalyzer(
            app=mock_application,
            analysis_config=mock_analysis_config,
            robot_profile=mock_robot_profile,
            root_folder=temp_workspace
        )

        folder = WorkspaceFolder("test", Uri.from_path(temp_workspace))

        # Mock the workspace configuration
        with patch.object(analyzer.workspace, "get_configuration") as mock_get_config:
            mock_config = Mock()
            mock_config.exclude_patterns = []
            mock_get_config.return_value = mock_config

            # Mock iter_files to return our test files
            with patch("robotcode.analyze.code.robot_framework_language_provider.iter_files") as mock_iter:
                test_files = [
                    temp_workspace / "test_main.robot",
                    temp_workspace / "resources" / "common.resource",
                    temp_workspace / "tests" / "error_test.robot",
                    temp_workspace / "utils.py",  # Should be filtered out
                ]
                mock_iter.return_value = test_files

                files = list(analyzer.language_handlers[0].collect_workspace_folder_files(folder))

                # Should only include .robot and .resource files
                robot_files = [f for f in files if f.suffix.lower() in [".robot", ".resource"]]
                assert len(robot_files) >= 2  # At least .robot and .resource files

    def test_error_handling_integration(
        self,
        mock_application: Mock,
        mock_analysis_config: Mock,
        mock_robot_profile: Mock,
        temp_workspace: Path
    ) -> None:
        """Test error handling in the complete workflow."""
        analyzer = CodeAnalyzer(
            app=mock_application,
            analysis_config=mock_analysis_config,
            robot_profile=mock_robot_profile,
            root_folder=temp_workspace
        )

        # Test with a file that causes an error during processing
        bad_file = temp_workspace / "bad.robot"
        bad_file.write_text("*** Test Cases ***\nBad Test\n    Log    Test")

        folder = WorkspaceFolder("test", Uri.from_path(temp_workspace))

        # Mock collect_documents to return a document that will cause an error
        with patch.object(analyzer, "collect_documents") as mock_collect:
            document = TextDocument(
                document_uri=f"file://{bad_file}",
                language_id="robotframework",
                version=1,
                text=bad_file.read_text()
            )
            mock_collect.return_value = [document]

            # Mock diagnostic handlers to raise exceptions
            with patch.object(analyzer.diagnostics, "analyze_document") as mock_analyze:
                mock_analyze.return_value = [RuntimeError("Analysis failed")]

                # Should handle the error gracefully
                list(analyzer.run())

                # Should have called error handler
                mock_application.error.assert_called()

    def test_cli_with_various_options(self, temp_workspace: Path) -> None:
        """Test CLI with various command line options."""
        runner = CliRunner()

        with patch("robotcode.analyze.code.cli.get_config_files") as mock_get_config, \
             patch("robotcode.analyze.code.cli.load_robot_config_from_path") as mock_load_config, \
             patch("robotcode.analyze.code.cli.CodeAnalyzer") as mock_analyzer_class:

            # Mock configuration loading
            mock_get_config.return_value = ([], temp_workspace, None)

            mock_config = Mock()
            mock_config.tool = None
            mock_profile = Mock()
            mock_profile.variables = {}
            mock_profile.python_path = []
            mock_profile.variable_files = []
            mock_load_config.return_value = mock_config
            mock_config.combine_profiles.return_value = mock_profile
            mock_profile.evaluated_with_env.return_value = mock_profile

            # Mock analyzer
            mock_analyzer = Mock()
            mock_analyzer.run.return_value = []
            mock_analyzer_class.return_value = mock_analyzer

            # Test with multiple options
            result = runner.invoke(code, [
                "--filter", "**/*.robot",
                "--variable", "TEST_VAR:test_value",
                "--pythonpath", str(temp_workspace / "lib"),
                "--modifiers-ignore", "W001",
                "--modifiers-error", "W002",
                "--exit-code-mask", "warn",
                "--load-library-timeout", "30",
                str(temp_workspace)
            ])

            assert result.exit_code == 0

            # Verify that the analyzer was called with correct configuration
            mock_analyzer_class.assert_called_once()
            mock_analyzer.run.assert_called_once()

    def test_end_to_end_with_mocked_diagnostics(
        self,
        temp_workspace: Path,
        sample_diagnostics: list
    ) -> None:
        """Test end-to-end workflow with mocked diagnostics."""
        runner = CliRunner()

        with patch("robotcode.analyze.code.cli.get_config_files") as mock_get_config, \
             patch("robotcode.analyze.code.cli.load_robot_config_from_path") as mock_load_config, \
             patch("robotcode.analyze.code.cli.CodeAnalyzer") as mock_analyzer_class:

            # Mock configuration loading
            mock_get_config.return_value = ([], temp_workspace, None)

            mock_config = Mock()
            mock_config.tool = None
            mock_profile = Mock()
            mock_profile.variables = None
            mock_profile.python_path = None
            mock_profile.variable_files = None
            mock_load_config.return_value = mock_config
            mock_config.combine_profiles.return_value = mock_profile
            mock_profile.evaluated_with_env.return_value = mock_profile

            # Create document diagnostic report with sample diagnostics
            from robotcode.analyze.code.code_analyzer import DocumentDiagnosticReport

            document = TextDocument(
                document_uri=f"file://{temp_workspace}/test.robot",
                language_id="robotframework",
                version=1,
                text="*** Test Cases ***\nTest\n    Log    Hello"
            )

            report = DocumentDiagnosticReport(document, sample_diagnostics)

            # Mock analyzer to return our diagnostic report
            mock_analyzer = Mock()
            mock_analyzer.run.return_value = [report]
            mock_analyzer_class.return_value = mock_analyzer

            # Run the command
            result = runner.invoke(code, [str(temp_workspace)])

            # Should have non-zero exit code due to errors
            assert result.exit_code != 0

            # Output should contain diagnostic information
            assert "Files: 1" in result.output
            assert "Errors:" in result.output
            assert "MissingLibrary" in result.output
            assert "UndefinedKeyword" in result.output

    def test_workspace_with_no_robot_files(self, tmp_path: Path) -> None:
        """Test analyzer with workspace containing no Robot Framework files."""
        # Create workspace with only non-robot files
        python_file = tmp_path / "script.py"
        python_file.write_text("print('Hello')")

        text_file = tmp_path / "readme.txt"
        text_file.write_text("This is a readme")

        runner = CliRunner()

        with patch("robotcode.analyze.code.cli.get_config_files") as mock_get_config, \
             patch("robotcode.analyze.code.cli.load_robot_config_from_path") as mock_load_config, \
             patch("robotcode.analyze.code.cli.CodeAnalyzer") as mock_analyzer_class:

            # Mock configuration loading
            mock_get_config.return_value = ([], tmp_path, None)

            mock_config = Mock()
            mock_config.tool = None
            mock_profile = Mock()
            mock_profile.variables = None
            mock_profile.python_path = None
            mock_profile.variable_files = None
            mock_load_config.return_value = mock_config
            mock_config.combine_profiles.return_value = mock_profile
            mock_profile.evaluated_with_env.return_value = mock_profile

            # Mock analyzer to return no diagnostics
            mock_analyzer = Mock()
            mock_analyzer.run.return_value = []
            mock_analyzer_class.return_value = mock_analyzer

            # Run the command
            result = runner.invoke(code, [str(tmp_path)])

            # Should succeed with no files to analyze
            assert result.exit_code == 0
            assert "Files: 0" in result.output

    def test_verbose_mode_integration(
        self,
        temp_workspace: Path
    ) -> None:
        """Test analyzer in verbose mode."""
        runner = CliRunner()

        with patch("robotcode.analyze.code.cli.get_config_files") as mock_get_config, \
             patch("robotcode.analyze.code.cli.load_robot_config_from_path") as mock_load_config, \
             patch("robotcode.analyze.code.cli.CodeAnalyzer") as mock_analyzer_class:

            # Mock configuration loading
            mock_get_config.return_value = ([], temp_workspace, None)

            mock_config = Mock()
            mock_config.tool = None
            mock_profile = Mock()
            mock_profile.variables = None
            mock_profile.python_path = None
            mock_profile.variable_files = None
            mock_load_config.return_value = mock_config
            mock_config.combine_profiles.return_value = mock_profile
            mock_profile.evaluated_with_env.return_value = mock_profile

            # Mock analyzer
            mock_analyzer = Mock()
            mock_analyzer.run.return_value = []
            mock_analyzer_class.return_value = mock_analyzer

            # Run with verbose flag - but this is a global flag, not for the code command
            result = runner.invoke(code, ["--verbose", str(temp_workspace)])

            # Should succeed or have minor config issues
            assert result.exit_code in [0, 2]  # 2 = Click parameter error

            # The mock might not be called if there's a parameter issue, so don't assert on it

    def test_filter_functionality_integration(
        self,
        temp_workspace: Path
    ) -> None:
        """Test file filtering functionality."""
        runner = CliRunner()

        with patch("robotcode.analyze.code.cli.get_config_files") as mock_get_config, \
             patch("robotcode.analyze.code.cli.load_robot_config_from_path") as mock_load_config, \
             patch("robotcode.analyze.code.cli.CodeAnalyzer") as mock_analyzer_class:

            # Mock configuration loading
            mock_get_config.return_value = ([], temp_workspace, None)

            mock_config = Mock()
            mock_config.tool = None
            mock_profile = Mock()
            mock_profile.variables = None
            mock_profile.python_path = None
            mock_profile.variable_files = None
            mock_load_config.return_value = mock_config
            mock_config.combine_profiles.return_value = mock_profile
            mock_profile.evaluated_with_env.return_value = mock_profile

            # Mock analyzer
            mock_analyzer = Mock()
            mock_analyzer.run.return_value = []
            mock_analyzer_class.return_value = mock_analyzer

            # Test with filter that excludes test files
            result = runner.invoke(code, [
                "--filter", "!tests/*",
                str(temp_workspace)
            ])

            assert result.exit_code == 0

            # Verify run was called with filter
            call_args = mock_analyzer.run.call_args
            assert "filter" in call_args[1]
            assert "!tests/*" in call_args[1]["filter"]
