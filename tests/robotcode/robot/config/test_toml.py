from robotcode.robot.config.loader import create_from_toml
from robotcode.robot.config.model import Mode


def test_toml() -> None:
    data = """\
args = ["abc"]
mode = "rpa"


[variables]
a=1
b = "this is a string"
c = [1, 2, "hello World"]


[listeners]
MyListener = []
Abc = ["def", 1]

[envs.default]
args = ["abc"]
python_path = ["abc", "def"]


[configs.devel]
mode = "default"

[configs.devel.listeners]
AnotherListener = ["default"]

[configs.devel_detached]
detached = true
mode = "default"

    """
    config = create_from_toml(data)
    assert config.args == ["abc"]
    assert config.variables == {"a": 1, "b": "this is a string", "c": [1, 2, "hello World"]}
    assert config.listeners == {"MyListener": [], "Abc": ["def", 1]}
    assert config.mode == Mode.RPA
