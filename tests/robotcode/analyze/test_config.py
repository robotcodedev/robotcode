
import pytest

from robotcode.analyze.config import (
    AnalyzeConfig,
    CodeConfig,
    ExitCodeMask,
    ModifiersConfig,
)


class TestExitCodeMask:
    """Test cases for ExitCodeMask enum."""

    def test_exit_code_mask_values(self) -> None:
        """Test ExitCodeMask flag values."""
        assert ExitCodeMask.NONE.value == 0
        assert ExitCodeMask.ERROR.value == 1
        assert ExitCodeMask.WARN.value == 2
        assert ExitCodeMask.INFO.value == 4
        assert ExitCodeMask.HINT.value == 8
        assert ExitCodeMask.ALL.value == 15  # 1 + 2 + 4 + 8

    def test_exit_code_mask_combinations(self) -> None:
        """Test ExitCodeMask flag combinations."""
        combined = ExitCodeMask.ERROR | ExitCodeMask.WARN
        assert combined.value == 3  # 1 + 2

        combined = ExitCodeMask.ERROR | ExitCodeMask.INFO | ExitCodeMask.HINT
        assert combined.value == 13  # 1 + 4 + 8

    def test_exit_code_mask_parse_single_values(self) -> None:
        """Test parsing single ExitCodeMask values."""
        assert ExitCodeMask.parse(["error"]) == ExitCodeMask.ERROR
        assert ExitCodeMask.parse(["warn"]) == ExitCodeMask.WARN
        assert ExitCodeMask.parse(["info"]) == ExitCodeMask.INFO
        assert ExitCodeMask.parse(["hint"]) == ExitCodeMask.HINT
        assert ExitCodeMask.parse(["all"]) == ExitCodeMask.ALL

    def test_exit_code_mask_parse_multiple_values(self) -> None:
        """Test parsing multiple ExitCodeMask values."""
        result = ExitCodeMask.parse(["error", "warn"])
        expected = ExitCodeMask.ERROR | ExitCodeMask.WARN
        assert result == expected

        result = ExitCodeMask.parse(["info", "hint"])
        expected = ExitCodeMask.INFO | ExitCodeMask.HINT
        assert result == expected

        result = ExitCodeMask.parse(["error", "warn", "info", "hint"])
        expected = ExitCodeMask.ALL
        assert result == expected

    def test_exit_code_mask_parse_empty_list(self) -> None:
        """Test parsing empty list returns NONE."""
        assert ExitCodeMask.parse([]) == ExitCodeMask.NONE
        assert ExitCodeMask.parse(None) == ExitCodeMask.NONE

    def test_exit_code_mask_parse_case_insensitive(self) -> None:
        """Test parsing is case insensitive."""
        assert ExitCodeMask.parse(["ERROR"]) == ExitCodeMask.ERROR
        assert ExitCodeMask.parse(["Warn"]) == ExitCodeMask.WARN
        assert ExitCodeMask.parse(["INFO"]) == ExitCodeMask.INFO
        assert ExitCodeMask.parse(["Hint"]) == ExitCodeMask.HINT
        assert ExitCodeMask.parse(["ALL"]) == ExitCodeMask.ALL

    def test_exit_code_mask_parse_invalid_value(self) -> None:
        """Test parsing invalid value raises KeyError."""
        with pytest.raises(KeyError):
            ExitCodeMask.parse(["invalid"])

        with pytest.raises(KeyError):
            ExitCodeMask.parse(["error", "invalid", "warn"])

    def test_exit_code_mask_parse_duplicate_values(self) -> None:
        """Test parsing duplicate values works correctly."""
        result = ExitCodeMask.parse(["error", "error", "warn"])
        expected = ExitCodeMask.ERROR | ExitCodeMask.WARN
        assert result == expected


class TestModifiersConfig:
    """Test cases for ModifiersConfig class."""

    def test_modifiers_config_default_initialization(self) -> None:
        """Test ModifiersConfig default initialization."""
        config = ModifiersConfig()

        assert config.ignore is None
        assert config.error is None
        assert config.warning is None
        assert config.information is None
        assert config.hint is None

    def test_modifiers_config_with_values(self) -> None:
        """Test ModifiersConfig with specified values."""
        config = ModifiersConfig(
            ignore=["W001", "W002"],
            error=["W003"],
            warning=["E001"],
            information=["E002"],
            hint=["I001"]
        )

        assert config.ignore == ["W001", "W002"]
        assert config.error == ["W003"]
        assert config.warning == ["E001"]
        assert config.information == ["E002"]
        assert config.hint == ["I001"]

    def test_modifiers_config_empty_lists(self) -> None:
        """Test ModifiersConfig with empty lists."""
        config = ModifiersConfig(
            ignore=[],
            error=[],
            warning=[],
            information=[],
            hint=[]
        )

        assert config.ignore == []
        assert config.error == []
        assert config.warning == []
        assert config.information == []
        assert config.hint == []


class TestCodeConfig:
    """Test cases for CodeConfig class."""

    def test_code_config_default_initialization(self) -> None:
        """Test CodeConfig default initialization."""
        config = CodeConfig()

        assert config.exit_code_mask is None

    def test_code_config_with_exit_code_mask(self) -> None:
        """Test CodeConfig with exit_code_mask."""
        config = CodeConfig(exit_code_mask=["error", "warn"])

        assert config.exit_code_mask == ["error", "warn"]

    def test_code_config_with_empty_exit_code_mask(self) -> None:
        """Test CodeConfig with empty exit_code_mask."""
        config = CodeConfig(exit_code_mask=[])

        assert config.exit_code_mask == []


class TestAnalyzeConfig:
    """Test cases for AnalyzeConfig class."""

    def test_analyze_config_default_initialization(self) -> None:
        """Test AnalyzeConfig default initialization."""
        config = AnalyzeConfig()

        assert config.modifiers is None
        assert config.code is None
        assert config.exclude_patterns is None
        assert config.load_library_timeout is None

    def test_analyze_config_with_modifiers(self) -> None:
        """Test AnalyzeConfig with modifiers."""
        modifiers = ModifiersConfig(
            ignore=["W001"],
            error=["W002"]
        )

        config = AnalyzeConfig(modifiers=modifiers)

        assert config.modifiers is modifiers
        assert config.modifiers.ignore == ["W001"]
        assert config.modifiers.error == ["W002"]

    def test_analyze_config_with_code(self) -> None:
        """Test AnalyzeConfig with code configuration."""
        code_config = CodeConfig(exit_code_mask=["warn", "info"])

        config = AnalyzeConfig(code=code_config)

        assert config.code is code_config
        assert config.code.exit_code_mask == ["warn", "info"]

    def test_analyze_config_with_exclude_patterns(self) -> None:
        """Test AnalyzeConfig with exclude_patterns."""
        config = AnalyzeConfig(exclude_patterns=["build/*", "*.tmp"])

        assert config.exclude_patterns == ["build/*", "*.tmp"]

    def test_analyze_config_with_load_library_timeout(self) -> None:
        """Test AnalyzeConfig with load_library_timeout."""
        config = AnalyzeConfig(load_library_timeout=30)

        assert config.load_library_timeout == 30

    def test_analyze_config_complete(self) -> None:
        """Test AnalyzeConfig with all fields set."""
        modifiers = ModifiersConfig(
            ignore=["W001", "W002"],
            error=["W003"],
            warning=["E001"],
            information=["E002"],
            hint=["I001"]
        )

        code_config = CodeConfig(exit_code_mask=["error", "warn"])

        config = AnalyzeConfig(
            modifiers=modifiers,
            code=code_config,
            exclude_patterns=["build/*", "*.tmp", "test_*"],
            load_library_timeout=60
        )

        assert config.modifiers is modifiers
        assert config.code is code_config
        assert config.exclude_patterns == ["build/*", "*.tmp", "test_*"]
        assert config.load_library_timeout == 60

    def test_to_workspace_analysis_config(self) -> None:
        """Test conversion to WorkspaceAnalysisConfig."""
        config = AnalyzeConfig(
            exclude_patterns=["build/*", "*.tmp"],
            load_library_timeout=45
        )

        workspace_config = config.to_workspace_analysis_config()

        # Check that the conversion works
        assert workspace_config is not None
        assert hasattr(workspace_config, "exclude_patterns")
        assert workspace_config.exclude_patterns == ["build/*", "*.tmp"]
        # Note: load_library_timeout is in robot config, not workspace config
        assert hasattr(workspace_config, "robot")
        assert workspace_config.robot.load_library_timeout == 45

    def test_to_workspace_analysis_config_with_none_values(self) -> None:
        """Test conversion to WorkspaceAnalysisConfig with None values."""
        config = AnalyzeConfig()

        workspace_config = config.to_workspace_analysis_config()

        # Should handle None values gracefully
        assert workspace_config is not None

    def test_to_workspace_analysis_config_preserves_non_none_values(self) -> None:
        """Test that conversion preserves non-None values."""
        config = AnalyzeConfig(
            exclude_patterns=["pattern1", "pattern2"],
            load_library_timeout=120
        )

        workspace_config = config.to_workspace_analysis_config()

        assert workspace_config.exclude_patterns == ["pattern1", "pattern2"]
        assert workspace_config.robot.load_library_timeout == 120


class TestConfigIntegration:
    """Integration tests for config classes."""

    def test_full_configuration_workflow(self) -> None:
        """Test a complete configuration workflow."""
        # Create modifiers configuration
        modifiers = ModifiersConfig(
            ignore=["DuplicateKeyword", "UnusedVariable"],
            error=["SyntaxError"],
            warning=["DeprecatedKeyword"],
            information=["CodeStyle"],
            hint=["Performance"]
        )

        # Create code configuration
        code_config = CodeConfig(exit_code_mask=["warn", "info"])

        # Create full analyze configuration
        analyze_config = AnalyzeConfig(
            modifiers=modifiers,
            code=code_config,
            exclude_patterns=["build/*", "temp/*", "*.pyc"],
            load_library_timeout=90
        )

        # Verify all values are set correctly
        assert analyze_config.modifiers.ignore == ["DuplicateKeyword", "UnusedVariable"]
        assert analyze_config.modifiers.error == ["SyntaxError"]
        assert analyze_config.modifiers.warning == ["DeprecatedKeyword"]
        assert analyze_config.modifiers.information == ["CodeStyle"]
        assert analyze_config.modifiers.hint == ["Performance"]

        assert analyze_config.code.exit_code_mask == ["warn", "info"]

        assert analyze_config.exclude_patterns == ["build/*", "temp/*", "*.pyc"]
        assert analyze_config.load_library_timeout == 90

        # Test conversion to workspace config
        workspace_config = analyze_config.to_workspace_analysis_config()
        assert workspace_config.exclude_patterns == ["build/*", "temp/*", "*.pyc"]
        assert workspace_config.robot.load_library_timeout == 90

    def test_partial_configuration(self) -> None:
        """Test configuration with only some fields set."""
        # Only set modifiers
        config = AnalyzeConfig(
            modifiers=ModifiersConfig(ignore=["W001"])
        )

        assert config.modifiers.ignore == ["W001"]
        assert config.code is None
        assert config.exclude_patterns is None
        assert config.load_library_timeout is None

    def test_config_modification(self) -> None:
        """Test modifying configuration after creation."""
        config = AnalyzeConfig()

        # Initially everything is None
        assert config.modifiers is None
        assert config.code is None

        # Set modifiers
        config.modifiers = ModifiersConfig(error=["E001"])
        assert config.modifiers.error == ["E001"]

        # Set code config
        config.code = CodeConfig(exit_code_mask=["error"])
        assert config.code.exit_code_mask == ["error"]

        # Set other fields
        config.exclude_patterns = ["temp/*"]
        config.load_library_timeout = 30

        assert config.exclude_patterns == ["temp/*"]
        assert config.load_library_timeout == 30
