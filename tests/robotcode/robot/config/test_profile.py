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
        match="Can't find any configuration profiles matching the pattern 'nonexistent'.",
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
    with pytest.raises(ValueError, match=".*invalid syntax.*"):
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
    with pytest.raises(TypeError, match=".*Value must be of type.*"):
        load_robot_config_from_robot_toml_str(data)
