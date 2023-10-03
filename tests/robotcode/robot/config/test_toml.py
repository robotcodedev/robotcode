from robotcode.robot.config.loader import load_robot_config_from_robot_toml_str


def test_toml() -> None:
    data = """\
args = ["abc"]
mode = "rpa"

[variables]
a="1"
b = "this is a string"
c = "asd"

[listeners]
MyListener = []
Abc = ["def", "1"]

[profiles.default]
description = "Default profile"
args = ["abc"]
python_path = ["abc", "def"]

# [profiles.devel]
# mode = "default"

[profiles.devel.listeners]
AnotherListener = ["default"]

[profiles.devel_detached]
detached = true
mode = "default"

    """
    config = load_robot_config_from_robot_toml_str(data)
    assert config.args == ["abc"]
    assert config.variables == {"a": "1", "b": "this is a string", "c": "asd"}
    assert config.listeners == {"MyListener": [], "Abc": ["def", "1"]}
    # assert config.mode == Mode.RPA
    assert config.profiles is not None
    assert config.profiles["default"].description == "Default profile"
    assert config.profiles["default"].args == ["abc"]
    assert config.profiles["devel"].listeners == {"AnotherListener": ["default"]}
