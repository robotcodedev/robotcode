import os
from pathlib import Path

import pytest

from robotcode.robot.config.loader import load_robot_config_from_path, load_robot_config_from_robot_toml_str
from robotcode.robot.config.model import RobotConfig


def test_can_parse_profiles() -> None:
    data = """\
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        args = ["abc"]

        [profiles.devel]
        description = "Development profile"
        args = ["devel"]
    """
    config = load_robot_config_from_robot_toml_str(data)
    assert config.python_path == ["abc", "def"]
    assert config.profiles
    assert config.profiles["default"].description == "Default profile"
    assert config.profiles["devel"].description == "Development profile"


def test_options_defined_in_profile_overrides_the_default_option() -> None:
    data = """\
        args = ["orig"]
        python_path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        args = ["default"]

        [profiles.devel]
        description = "Development profile"
        args = ["devel"]
    """
    config = load_robot_config_from_robot_toml_str(data)

    profile = config.combine_profiles()
    assert profile
    assert profile.args == ["orig"]

    profile = config.combine_profiles("default")
    assert profile
    assert profile.args == ["default"]

    profile = config.combine_profiles("devel")
    assert profile
    assert profile.args == ["devel"]


def test_extends_options_defined_in_profile_appends_to_default_option() -> None:
    data = """\
        args = ["orig"]
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extend-args = ["default"]

        [profiles.devel]
        description = "Development profile"
        extend-args = ["devel"]
    """
    config = load_robot_config_from_robot_toml_str(data)

    profile = config.combine_profiles()
    assert profile
    assert profile.args == ["orig"]

    profile = config.combine_profiles("default")
    assert profile
    assert profile.args == ["orig", "default"]

    profile = config.combine_profiles("devel")
    assert profile
    assert profile.args == ["orig", "devel"]

    profile = config.combine_profiles("default", "devel")
    assert profile
    assert profile.args == ["orig", "default", "devel"]


def test_if_profile_is_not_defined_an_error_is_raised() -> None:
    data = """\
        args = ["orig"]
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extend-args = ["default"]

        [profiles.devel]
        description = "Development profile"
        extend-args = ["devel"]
    """
    config = load_robot_config_from_robot_toml_str(data)

    with pytest.raises(
        ValueError,
        match=r"Can't find any configuration profiles matching the pattern 'nonexistent'.",
    ):
        config.combine_profiles("nonexistent")


def test_profiles_can_be_selected_by_wildcards() -> None:
    data = """\
        args = ["orig"]
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extend-args = ["default"]

        [profiles.devel]
        description = "Development profile"
        extend-args = ["devel"]

        [profiles.ci]
        description = "CI profile"
        extend-args = ["ci"]

    """
    config = load_robot_config_from_robot_toml_str(data)

    profile = config.combine_profiles("de*")
    assert profile
    assert profile.args == ["orig", "default", "devel"]

    profile = config.combine_profiles("?e*")
    assert profile
    assert profile.args == ["orig", "default", "devel"]


def test_profiles_can_be_disabled() -> None:
    data = """\
        args = ["orig"]
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extend-args = ["default"]

        [profiles.devel]
        enabled=false
        description = "Development profile"
        extend-args = ["devel"]

        [profiles.ci]
        enabled=true
        description = "CI profile"
        extend-args = ["ci"]
        """
    config = load_robot_config_from_robot_toml_str(data)

    profile = config.combine_profiles("*")
    assert profile
    assert profile.args == ["orig", "default", "ci"]


def test_profiles_enabled_can_be_an_condition() -> None:
    data = """\
        args = ["orig"]
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extend-args = ["default"]

        [profiles.devel]
        enabled=false
        description = "Development profile"
        extend-args = ["devel"]

        [profiles.another-ci]
        enabled={if='environ.get("ANOTHER-CI") == "true"'}
        description = "Another CI profile"
        extend-args = ["another-ci"]

        [profiles.ci]
        enabled={if='environ.get("CI") == "true"'}
        description = "CI profile"
        extend-args = ["ci"]
        """
    config = load_robot_config_from_robot_toml_str(data)
    os.environ["CI"] = "true"
    profile = config.combine_profiles("*")
    assert profile
    assert profile.args == ["orig", "default", "ci"]


def test_profiles_enabled_cant_be_an_invalid_condition() -> None:
    data = """\
        args = ["orig"]
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extend-args = ["default"]

        [profiles.devel]
        enabled=false
        description = "Development profile"
        extend-args = ["devel"]

        [profiles.another-ci]
        enabled={if='environ.get("ANOTHER-CI") == "true"'}
        description = "Another CI profile"
        extend-args = ["another-ci"]

        [profiles.ci]
        enabled={if='environ.get("CI") = "true"'}
        description = "CI profile"
        extend-args = ["ci"]
        """
    config = load_robot_config_from_robot_toml_str(data)
    os.environ["CI"] = "true"
    with pytest.raises(ValueError, match=r".*invalid syntax.*"):
        config.combine_profiles("*")


def test_profiles_precedence_defines_the_order() -> None:
    data = """\
        args = ["orig"]

        [profiles.default]
        extend-args = ["default"]
        precedence = 4

        [profiles.devel]
        extend-args = ["devel"]
        precedence = 3

        [profiles.another-ci]
        extend-args = ["another-ci"]
        precedence = 2

        [profiles.ci]
        extend-args = ["ci"]
        precedence = 1
        """
    config = load_robot_config_from_robot_toml_str(data)
    profile = config.combine_profiles("*")
    assert profile.args == ["orig", "ci", "another-ci", "devel", "default"]


def test_profiles_tag_stat_combine_generates_correct() -> None:
    data = """\
        tag-stat-combine = ["tag1:tag2", {"tag3" = "tag4"}]
        extend-tag-stat-combine = ["tag1:tag2", {"tag3" = "tag4"}]
        """
    config = load_robot_config_from_robot_toml_str(data)
    cmd_line = config.combine_profiles().evaluated().build_command_line()
    assert cmd_line == [
        "--tagstatcombine",
        "tag1:tag2",
        "--tagstatcombine",
        "tag3:tag4",
    ]


def test_profiles_flatten_keywords_supports_literals_and_patterns() -> None:
    data = """\
        flatten_keywords = ["for", "while", "iteration", {"name" = "tag4"}, {tag="tag5"}, "foritem"]
        """
    config = load_robot_config_from_robot_toml_str(data)
    cmd_line = config.combine_profiles().evaluated().build_command_line()
    assert cmd_line == [
        "--flattenkeywords",
        "for",
        "--flattenkeywords",
        "while",
        "--flattenkeywords",
        "iteration",
        "--flattenkeywords",
        "name:tag4",
        "--flattenkeywords",
        "tag:tag5",
        "--flattenkeywords",
        "foritem",
    ]


def test_set_and_evaluates_environment_var_correctly() -> None:
    os.environ.pop("ENV_TEST_VAR", None)
    os.environ.pop("ENV_TEST_VAR_CALCULATED", None)
    data = """\
        [env]
        ENV_TEST_VAR = "test"
        ENV_TEST_VAR_CALCULATED = { expr = "1+2"}

        [variables]
        TEST_VAR = { expr = "environ.get('ENV_TEST_VAR')"}
        TEST_VAR_CALCULATED = { expr = "environ.get('ENV_TEST_VAR_CALCULATED')"}
        """
    config = load_robot_config_from_robot_toml_str(data)
    evaluated = config.combine_profiles().evaluated_with_env()
    assert evaluated.variables
    assert evaluated.variables["TEST_VAR"] == "test"
    assert evaluated.variables["TEST_VAR_CALCULATED"] == "3"


def test_set_and_evaluates_environment_var_correctly_with_vars_overridden_in_profile() -> None:
    os.environ.pop("ENV_TEST_VAR", None)
    os.environ.pop("ENV_TEST_VAR_CALCULATED", None)
    data = """\
        [env]
        ENV_TEST_VAR = "test"
        ENV_TEST_VAR_CALCULATED = { expr = "1+2"}

        [variables]
        TEST_VAR = { expr = "environ.get('ENV_TEST_VAR')"}
        TEST_VAR_CALCULATED = { expr = "environ.get('ENV_TEST_VAR_CALCULATED')"}

        [profiles.test.extend-env]
        ENV_TEST_VAR = "test overridden"
        ENV_TEST_VAR_CALCULATED = { expr = "3*3"}

        """
    config = load_robot_config_from_robot_toml_str(data)
    evaluated = config.combine_profiles("test").evaluated_with_env()
    assert evaluated.variables
    assert evaluated.variables["TEST_VAR"] == "test overridden"
    assert evaluated.variables["TEST_VAR_CALCULATED"] == "9"


def test_str_expression_works_correctly_in_lists_in_build_command_line() -> None:
    data = """\
        [listeners]
        dummy_listener = [
            { expr = "'dummy' + '/output'" },
        ]
        listener_with_colon = ["dummy:output"]
        """
    config = load_robot_config_from_robot_toml_str(data)
    evaluated = config.combine_profiles().evaluated_with_env()
    cmd_line = evaluated.build_command_line()

    assert cmd_line
    assert cmd_line == ["--listener", "dummy_listener:dummy/output", "--listener", "listener_with_colon;dummy:output"]


def test_type_that_wants_alist_should_throw_an_error() -> None:
    data = """\
            [listeners]
            listener_with_colon = "dummy:output"
            """
    with pytest.raises(TypeError, match=r".*Value '.*' must be of type.*"):
        load_robot_config_from_robot_toml_str(data)


def test_rebot_options_are_read_from_the_rebot_section() -> None:
    data = """\
        console = "dotted"

        [rebot]
        console = "quiet"
        quiet = true
    """
    config = load_robot_config_from_robot_toml_str(data)

    assert config.console == "dotted"
    assert config.rebot is not None
    assert config.rebot.console == "quiet"
    assert config.rebot.quiet is True


def test_profile_with_a_setting_and_its_extend_setting_uses_both() -> None:
    data = """\
        [variables]
        BROWSER = "chrome"

        [profiles.dev]
        variables = { A = "1" }
        extend-variables = { B = "2" }
    """
    config = load_robot_config_from_robot_toml_str(data)

    assert config.combine_profiles("dev").variables == {"A": "1", "B": "2"}


def load_robot_toml_and_local_robot_toml(tmp_path: Path, robot_toml: str, local_robot_toml: str) -> RobotConfig:
    (tmp_path / "robot.toml").write_text(robot_toml, encoding="utf-8")
    (tmp_path / ".robot.toml").write_text(local_robot_toml, encoding="utf-8")
    return load_robot_config_from_path(tmp_path / "robot.toml", tmp_path / ".robot.toml")


def test_a_file_with_a_setting_and_its_extend_setting_uses_both(tmp_path: Path) -> None:
    config = load_robot_toml_and_local_robot_toml(
        tmp_path,
        """\
        [variables]
        BROWSER = "chrome"
        """,
        """\
        variables = { A = "1" }
        extend-variables = { B = "2" }
        """,
    )

    assert config.combine_profiles().variables == {"A": "1", "B": "2"}


def test_extend_profiles_extends_a_setting_of_the_profile(tmp_path: Path) -> None:
    config = load_robot_toml_and_local_robot_toml(
        tmp_path,
        """\
        [profiles.dev]
        variables = { A = "1" }
        """,
        """\
        [extend-profiles.dev]
        extend-variables = { B = "2" }
        """,
    )

    assert config.combine_profiles("dev").variables == {"A": "1", "B": "2"}


def test_extend_profiles_extends_the_extend_setting_of_the_profile(tmp_path: Path) -> None:
    config = load_robot_toml_and_local_robot_toml(
        tmp_path,
        """\
        [variables]
        BROWSER = "chrome"

        [profiles.dev]
        extend-variables = { A = "1" }
        """,
        """\
        [extend-profiles.dev]
        extend-variables = { B = "2" }
        """,
    )

    assert config.combine_profiles("dev").variables == {"BROWSER": "chrome", "A": "1", "B": "2"}


def test_extend_profiles_replaces_a_setting_given_without_extend(tmp_path: Path) -> None:
    config = load_robot_toml_and_local_robot_toml(
        tmp_path,
        """\
        [variables]
        BROWSER = "chrome"

        [profiles.dev]
        extend-variables = { A = "1" }
        """,
        """\
        [extend-profiles.dev]
        variables = { B = "2" }
        """,
    )

    assert config.combine_profiles("dev").variables == {"B": "2"}


def test_extend_profiles_adds_a_new_profile(tmp_path: Path) -> None:
    config = load_robot_toml_and_local_robot_toml(
        tmp_path,
        """\
        [profiles.dev]
        description = "Dev"
        """,
        """\
        [extend-profiles.local]
        description = "Local"
        """,
    )

    assert config.profiles is not None
    assert sorted(config.profiles) == ["dev", "local"]


def test_extend_rebot_in_a_profile_changes_the_rebot_table() -> None:
    data = """\
        [rebot]
        merge = true

        [profiles.ci.extend-rebot]
        report-title = "CI"
    """
    config = load_robot_config_from_robot_toml_str(data)

    rebot = config.combine_profiles("ci").rebot
    assert rebot is not None
    assert rebot.merge is True
    assert rebot.report_title == "CI"

    # applying the profile does not change the configuration's own table
    assert config.rebot is not None
    assert config.rebot.report_title is None
    rebot_without_profile = config.combine_profiles().rebot
    assert rebot_without_profile is not None
    assert rebot_without_profile.report_title is None


def test_extend_rebot_in_a_later_file_changes_the_rebot_table(tmp_path: Path) -> None:
    config = load_robot_toml_and_local_robot_toml(
        tmp_path,
        """\
        [rebot]
        merge = true
        """,
        """\
        [extend-rebot]
        report-title = "Mine"
        """,
    )

    rebot = config.combine_profiles().rebot
    assert rebot is not None
    assert rebot.merge is True
    assert rebot.report_title == "Mine"


def test_extend_rebot_in_extend_profiles_changes_the_rebot_table_of_the_profile(tmp_path: Path) -> None:
    config = load_robot_toml_and_local_robot_toml(
        tmp_path,
        """\
        [profiles.ci.rebot]
        merge = true
        """,
        """\
        [extend-profiles.ci.extend-rebot]
        log-title = "Mine"
        """,
    )

    rebot = config.combine_profiles("ci").rebot
    assert rebot is not None
    assert rebot.merge is True
    assert rebot.log_title == "Mine"


def test_rebot_in_a_later_file_replaces_the_rebot_table(tmp_path: Path) -> None:
    config = load_robot_toml_and_local_robot_toml(
        tmp_path,
        """\
        [rebot]
        merge = true
        """,
        """\
        [rebot]
        report-title = "Mine"
        """,
    )

    rebot = config.combine_profiles().rebot
    assert rebot is not None
    assert rebot.merge is None
    assert rebot.report_title == "Mine"
