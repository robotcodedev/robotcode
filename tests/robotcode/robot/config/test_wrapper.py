"""Tests for the `wrapper` / `extend-wrapper` profile option that backs the
session-wrapper feature (`robot.toml` `wrapper`, `robotcode --wrapper`)."""

from robotcode.robot.config.loader import load_robot_config_from_robot_toml_str


def test_wrapper_parses_as_a_list() -> None:
    config = load_robot_config_from_robot_toml_str('wrapper = ["xvfb-run", "-a"]')
    assert config.wrapper == ["xvfb-run", "-a"]


def test_wrapper_defaults_to_none_when_unset() -> None:
    config = load_robot_config_from_robot_toml_str('args = ["x"]')
    assert config.combine_profiles().wrapper is None


def test_profile_wrapper_overrides_the_default_wrapper() -> None:
    data = """\
        wrapper = ["root"]

        [profiles.default]
        wrapper = ["default-wrap"]

        [profiles.x11]
        wrapper = ["x11-wrap", "--"]
    """
    config = load_robot_config_from_robot_toml_str(data)

    assert config.combine_profiles().wrapper == ["root"]
    assert config.combine_profiles("default").wrapper == ["default-wrap"]
    assert config.combine_profiles("x11").wrapper == ["x11-wrap", "--"]


def test_extend_wrapper_appends_to_the_default_wrapper() -> None:
    data = """\
        wrapper = ["base"]

        [profiles.ci]
        extend-wrapper = ["--flag"]
    """
    config = load_robot_config_from_robot_toml_str(data)

    assert config.combine_profiles().wrapper == ["base"]
    assert config.combine_profiles("ci").wrapper == ["base", "--flag"]
