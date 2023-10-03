import os

import pytest
from robotcode.robot.config.loader import load_robot_config_from_robot_toml_str


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


def test_extra_options_defined_in_profile_appends_to_default_option() -> None:
    data = """\
        args = ["orig"]
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extra-args = ["default"]

        [profiles.devel]
        description = "Development profile"
        extra-args = ["devel"]
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
        extra-args = ["default"]

        [profiles.devel]
        description = "Development profile"
        extra-args = ["devel"]
    """
    config = load_robot_config_from_robot_toml_str(data)

    with pytest.raises(ValueError, match="Can't find any profiles matching the pattern 'nonexistent'."):
        config.combine_profiles("nonexistent")


def test_profiles_can_be_selected_by_wildcards() -> None:
    data = """\
        args = ["orig"]
        python-path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extra-args = ["default"]

        [profiles.devel]
        description = "Development profile"
        extra-args = ["devel"]

        [profiles.ci]
        description = "CI profile"
        extra-args = ["ci"]

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
        extra-args = ["default"]

        [profiles.devel]
        enabled=false
        description = "Development profile"
        extra-args = ["devel"]

        [profiles.ci]
        enabled=true
        description = "CI profile"
        extra-args = ["ci"]
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
        extra-args = ["default"]

        [profiles.devel]
        enabled=false
        description = "Development profile"
        extra-args = ["devel"]

        [profiles.another-ci]
        enabled={if='environ.get("ANOTHER-CI") == "true"'}
        description = "Another CI profile"
        extra-args = ["another-ci"]

        [profiles.ci]
        enabled={if='environ.get("CI") == "true"'}
        description = "CI profile"
        extra-args = ["ci"]
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
        extra-args = ["default"]

        [profiles.devel]
        enabled=false
        description = "Development profile"
        extra-args = ["devel"]

        [profiles.another-ci]
        enabled={if='environ.get("ANOTHER-CI") == "true"'}
        description = "Another CI profile"
        extra-args = ["another-ci"]

        [profiles.ci]
        enabled={if='environ.get("CI") = "true"'}
        description = "CI profile"
        extra-args = ["ci"]
        """
    config = load_robot_config_from_robot_toml_str(data)
    os.environ["CI"] = "true"
    with pytest.raises(ValueError, match=".*invalid syntax.*"):
        config.combine_profiles("*")


def test_profiles_precedence_defines_the_order() -> None:
    data = """\
        args = ["orig"]

        [profiles.default]
        extra-args = ["default"]
        precedence = 4

        [profiles.devel]
        extra-args = ["devel"]
        precedence = 3

        [profiles.another-ci]
        extra-args = ["another-ci"]
        precedence = 2

        [profiles.ci]
        extra-args = ["ci"]
        precedence = 1
        """
    config = load_robot_config_from_robot_toml_str(data)
    profile = config.combine_profiles("*")
    assert profile.args == ["orig", "ci", "another-ci", "devel", "default"]


def test_profiles_tag_stat_combine_generates_correct() -> None:
    data = """\
        tag-stat-combine = ["tag1:tag2", {"tag3" = "tag4"}]
        extra-tag-stat-combine = ["tag1:tag2", {"tag3" = "tag4"}]
        """
    config = load_robot_config_from_robot_toml_str(data)
    cmd_line = config.combine_profiles().evaluated().build_command_line()
    assert cmd_line == ["--tagstatcombine", "tag1:tag2", "--tagstatcombine", "tag3:tag4"]


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
