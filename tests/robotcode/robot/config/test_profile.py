import os
from pathlib import Path
from typing import List

import pytest

from robotcode.robot.config.loader import load_robot_config_from_path, load_robot_config_from_robot_toml_str
from robotcode.robot.config.model import ProfileInheritanceError, ProfileNotFoundError, RobotConfig, UnknownProfile


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

    with pytest.raises(ValueError, match=r"No profile matches 'nonexistent'\."):
        config.combine_profiles("nonexistent")


# the commands pass an error_callback for the errors that are only reported, such as those of `enabled` conditions
def test_a_name_that_selects_no_profile_is_an_error_also_with_an_error_callback() -> None:
    data = """\
        [profiles.ci]
        extend-args = ["ci"]
        """
    errors: List[str] = []

    with pytest.raises(ProfileNotFoundError) as e:
        load_robot_config_from_robot_toml_str(data).combine_profiles(
            "missing", error_callback=lambda message: errors.append(str(message))
        )

    assert e.value.unknown == UnknownProfile("missing")
    assert errors == []


def test_a_default_profile_that_does_not_exist_is_reported_and_the_other_default_profiles_apply() -> None:
    data = """\
        args = ["orig"]
        default-profiles = ["typo", "ci"]

        [profiles.ci]
        extend-args = ["ci"]
        """
    errors: List[str] = []

    profile = load_robot_config_from_robot_toml_str(data).combine_profiles(
        error_callback=lambda message: errors.append(str(message))
    )

    assert profile.args == ["orig", "ci"]
    assert errors == ["No profile matches 'typo'."]


def test_a_default_profile_that_does_not_exist_is_an_error_without_an_error_callback() -> None:
    data = """\
        default-profiles = ["typo"]

        [profiles.ci]
        extend-args = ["ci"]
        """

    with pytest.raises(ProfileNotFoundError) as e:
        load_robot_config_from_robot_toml_str(data).combine_profiles()

    assert e.value.unknown == UnknownProfile("typo", default=True)


# a later file's `profiles` replace those of the user configuration, while its `default-profiles` stay
def test_a_default_profile_of_the_user_configuration_that_the_project_replaces_is_reported(tmp_path: Path) -> None:
    user_config = tmp_path / "user.toml"
    user_config.write_text('default-profiles = ["mine"]\n\n[profiles.mine]\nextend-args = ["mine"]\n', encoding="utf-8")
    project_config = tmp_path / "robot.toml"
    project_config.write_text('[profiles.ci]\nextend-args = ["ci"]\n', encoding="utf-8")
    errors: List[str] = []

    load_robot_config_from_path(user_config, project_config).combine_profiles(
        error_callback=lambda message: errors.append(str(message))
    )

    assert errors == ["No profile matches 'mine'."]


def test_an_inherited_profile_that_does_not_exist_is_an_error() -> None:
    data = """\
        [profiles.ci]
        inherits = ["typo"]
        extend-args = ["ci"]
        """

    with pytest.raises(ProfileNotFoundError) as e:
        load_robot_config_from_robot_toml_str(data).combine_profiles("ci", error_callback=lambda message: None)

    assert e.value.unknown == UnknownProfile("typo", inherited_by="ci")


def test_names_that_select_no_profile_go_to_the_callback_and_the_other_profiles_apply() -> None:
    data = """\
        args = ["orig"]

        [profiles.ci]
        inherits = ["typo"]
        extend-args = ["ci"]
        """
    unknown: List[UnknownProfile] = []

    profile = load_robot_config_from_robot_toml_str(data).combine_profiles(
        "missing", "ci", unknown_profile_callback=unknown.append
    )

    assert profile.args == ["orig", "ci"]
    assert [(u.name, u.selected, u.inherited_by) for u in unknown] == [("missing", True, None), ("typo", False, "ci")]


def test_a_name_that_selects_no_profile_is_reported_once_for_each_place_it_comes_from() -> None:
    data = """\
        [profiles.chrome]
        inherits = ["base"]

        [profiles.firefox]
        inherits = ["base"]

        [profiles.base]
        inherits = ["comon"]
        """
    unknown: List[UnknownProfile] = []

    load_robot_config_from_robot_toml_str(data).combine_profiles(
        "chrome", "firefox", "typo", "typo", unknown_profile_callback=unknown.append
    )

    assert [(u.name, u.inherited_by) for u in unknown] == [("comon", "base"), ("typo", None)]


def test_an_exact_name_selects_its_profile_also_with_pattern_characters() -> None:
    data = """\
        args = ["orig"]

        [profiles."ci[eu]"]
        extend-args = ["eu"]

        [profiles.cie]
        extend-args = ["cie"]
        """

    profile = load_robot_config_from_robot_toml_str(data).combine_profiles("ci[eu]")

    assert profile.args == ["orig", "eu"]


def test_a_pattern_in_inherits_does_not_match_the_profile_that_has_it() -> None:
    data = """\
        args = ["orig"]

        [profiles.ci-base]
        extend-args = ["base"]

        [profiles.ci-linux]
        inherits = ["ci-*"]
        extend-args = ["linux"]
        """

    profile = load_robot_config_from_robot_toml_str(data).combine_profiles("ci-linux")

    assert profile.args == ["orig", "base", "linux"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            '[profiles.a]\ninherits = ["b"]\n\n[profiles.b]\ninherits = ["a"]\n',
            "The profile 'a' inherits itself: a -> b -> a.",
        ),
        ('[profiles.a]\ninherits = ["a"]\n', "The profile 'a' inherits itself: a -> a."),
    ],
)
def test_a_profile_that_inherits_itself_is_an_error_also_for_callers_that_go_on(data: str, message: str) -> None:
    with pytest.raises(ProfileInheritanceError) as e:
        load_robot_config_from_robot_toml_str(data).combine_profiles(
            "a", error_callback=lambda message: None, unknown_profile_callback=lambda unknown: None
        )

    assert str(e.value) == message


@pytest.mark.parametrize(
    "unknown",
    [UnknownProfile("typo"), UnknownProfile("typo", default=True), UnknownProfile("typo", inherited_by="ci")],
)
def test_the_message_names_only_the_name_whatever_it_comes_from(unknown: UnknownProfile) -> None:
    assert unknown.message == "No profile matches 'typo'."


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


INHERITANCE_CHAIN = """\
    args = ["orig"]

    [profiles.base]
    extend-args = ["base"]

    [profiles.staging]
    inherits = ["base"]
    extend-args = ["staging"]

    [profiles.ci]
    inherits = ["staging"]
    extend-args = ["ci"]

    [profiles.nightly]
    inherits = ["staging"]
    extend-args = ["nightly"]
    """


def _chain(*disabled: str) -> RobotConfig:
    """The profiles of INHERITANCE_CHAIN, with the given ones disabled."""
    config = load_robot_config_from_robot_toml_str(INHERITANCE_CHAIN)
    assert config.profiles
    for name in disabled:
        config.profiles[name].enabled = False
    return config


def test_a_profile_brings_the_profiles_it_inherits_from_along() -> None:
    profile = _chain().combine_profiles("ci")

    assert profile.args == ["orig", "base", "staging", "ci"]


def test_a_disabled_profile_brings_no_profiles_it_inherits_from_along_at_any_depth() -> None:
    profile = _chain("ci").combine_profiles("ci")

    assert profile.args == ["orig"]


def test_a_disabled_inherited_profile_is_left_out_with_the_profiles_it_inherits_from() -> None:
    profile = _chain("staging").combine_profiles("ci")

    assert profile.args == ["orig", "ci"]


def test_an_inherited_profile_is_used_when_one_of_the_profiles_that_inherit_it_is_used() -> None:
    profile = _chain("ci").combine_profiles("ci", "nightly")

    assert profile.args == ["orig", "base", "staging", "nightly"]


def test_a_selected_profile_is_used_although_a_disabled_profile_inherits_it() -> None:
    profile = _chain("ci").combine_profiles("ci", "base")

    assert profile.args == ["orig", "base"]


def test_an_error_in_the_condition_of_an_inheriting_profile_is_reported_once() -> None:
    data = """\
        args = ["orig"]

        [profiles.base]
        extend-args = ["base"]

        [profiles.ci]
        enabled = {if = 'environ.get("CI") = "true"'}
        inherits = ["base"]
        extend-args = ["ci"]
        """
    errors: List[str] = []

    profile = load_robot_config_from_robot_toml_str(data).combine_profiles(
        "ci", error_callback=lambda message: errors.append(str(message))
    )

    assert profile.args == ["orig"]
    assert len(errors) == 1
    assert errors[0].startswith("Error evaluating 'enabled' condition for profile 'ci'")


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
