import os

import pytest

from robotcode.robot.config.loader import loads_config_from_robot_toml


def test_can_parse_profiles() -> None:
    data = """\
        python_path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        args = ["abc"]

        [profiles.devel]
        description = "Development profile"
        args = ["devel"]
    """
    config = loads_config_from_robot_toml(data)
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
    config = loads_config_from_robot_toml(data)

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
        python_path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extra-args = ["default"]

        [profiles.devel]
        description = "Development profile"
        extra-args = ["devel"]
    """
    config = loads_config_from_robot_toml(data)

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
        python_path = ["abc", "def"]

        [variables]
        a="1"

        [profiles.default]
        description = "Default profile"
        extra-args = ["default"]

        [profiles.devel]
        description = "Development profile"
        extra-args = ["devel"]
    """
    config = loads_config_from_robot_toml(data)

    with pytest.raises(ValueError, match="Can't find any profiles matching the pattern 'nonexistent''."):
        config.combine_profiles("nonexistent")


def test_profiles_can_be_selected_by_wildcards() -> None:
    data = """\
        args = ["orig"]
        python_path = ["abc", "def"]

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
    config = loads_config_from_robot_toml(data)

    profile = config.combine_profiles("de*")
    assert profile
    assert profile.args == ["orig", "default", "devel"]

    profile = config.combine_profiles("?e*")
    assert profile
    assert profile.args == ["orig", "default", "devel"]


def test_profiles_can_be_disabled() -> None:
    data = """\
        args = ["orig"]
        python_path = ["abc", "def"]

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
    config = loads_config_from_robot_toml(data)

    profile = config.combine_profiles("*")
    assert profile
    assert profile.args == ["orig", "default", "ci"]


def test_profiles_enabled_can_be_an_condition() -> None:
    data = """\
        args = ["orig"]
        python_path = ["abc", "def"]

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
        enabled={if='env.get("ANOTHER-CI") == "true"'}
        description = "Another CI profile"
        extra-args = ["another-ci"]

        [profiles.ci]
        enabled={if='env.get("CI") == "true"'}
        description = "CI profile"
        extra-args = ["ci"]
        """
    config = loads_config_from_robot_toml(data)
    os.environ["CI"] = "true"
    profile = config.combine_profiles("*")
    assert profile
    assert profile.args == ["orig", "default", "ci"]


def test_profiles_enabled_cant_be_an_invalid_condition() -> None:
    data = """\
        args = ["orig"]
        python_path = ["abc", "def"]

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
        enabled={if='env.get("ANOTHER-CI") == "true"'}
        description = "Another CI profile"
        extra-args = ["another-ci"]

        [profiles.ci]
        enabled={if='env.get("CI") = "true"'}
        description = "CI profile"
        extra-args = ["ci"]
        """
    config = loads_config_from_robot_toml(data)
    os.environ["CI"] = "true"
    profile = config.combine_profiles("*")
    assert profile
    assert profile.args == ["orig", "default"]
