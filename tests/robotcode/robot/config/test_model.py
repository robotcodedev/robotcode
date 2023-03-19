from typing import Any, Dict

import pytest

from robotcode.core.dataclasses import TypeValidationError, as_dict, from_dict
from robotcode.robot.config.model import Mode, RobotConfig


def test_robot_config_default() -> None:
    model = RobotConfig()

    assert model.args == []
    assert model.python_path == []
    assert model.env == {}
    assert model.variables == {}
    assert model.variable_files == []
    assert model.paths == []
    assert model.output_dir is None
    assert model.output_file is None
    assert model.log_file is None
    assert model.debug_file is None
    assert model.log_level is None
    assert model.console is None
    assert model.languages == []
    assert model.parsers == {}
    assert model.mode is None


@pytest.mark.parametrize(
    ("kwargs"),
    [
        ({"args": 1}),
        ({"python_path": 1}),
        ({"env": 1}),
        ({"output_dir": 1}),
        ({"args": 1, "output_dir": 1}),
    ],
)
def test_robot_config_cannot_assign_invalid_args(kwargs: Dict[str, Any]) -> None:
    with pytest.raises(TypeValidationError):
        RobotConfig(**kwargs)


def test_robot_config_can_created_from_dict() -> None:
    data: Dict[str, Any] = {
        "args": ["--argument"],
        "python_path": ["asd"],
        "env": {},
        "variables": {"a": 1},
        "variable_files": [],
        "paths": [],
        "console": None,
        "output_dir": None,
        "output_file": None,
        "log_file": None,
        "debug_file": None,
        "log_level": None,
        "languages": [],
        "parsers": {},
        "pre_run_modifiers": {},
        "pre_rebot_modifiers": {},
        "listeners": {},
        "mode": "default",
    }
    model = from_dict(data, RobotConfig)
    data["mode"] = Mode.DEFAULT
    model_dict = as_dict(model)
    for key in data:
        assert model_dict[key] == data[key]
