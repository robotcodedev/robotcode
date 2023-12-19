from typing import Any, Dict

import pytest
from robotcode.core.utils.dataclasses import TypeValidationError, as_dict, from_dict
from robotcode.robot.config.model import RobotConfig


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
        "python-path": ["asd"],
        "env": {},
        "variables": {"a": "1"},
        "variable-files": [],
        "paths": [],
        "console": None,
        "output-dir": None,
        "output": None,
        "log": None,
        "debug-file": None,
        "log-level": None,
        "languages": [],
        "pre-run-modifiers": {},
        "pre-rebot-modifiers": {},
        "listeners": {},
        "rpa": True,
    }
    model = from_dict(data, RobotConfig)
    model_dict = as_dict(model)
    for key in data:
        assert model_dict[key] == data[key], key
