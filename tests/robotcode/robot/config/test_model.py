from typing import Any, Dict, List

import pytest

from robotcode.core.utils.dataclasses import (
    NamedTypeError,
    TypeValidationError,
    as_dict,
    from_dict,
)
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
def test_robot_config_cannot_assign_invalid_args(
    kwargs: Dict[str, Any],
) -> None:
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


@pytest.mark.parametrize(
    ("value", "expected_args"),
    [
        (40, ["--maxerrorlines", "40"]),
        ("NONE", ["--maxerrorlines", "NONE"]),
    ],
)
def test_max_error_lines_accepts_int_and_none_string(value: Any, expected_args: List[str]) -> None:
    model = from_dict({"max-error-lines": value}, RobotConfig)
    assert model.max_error_lines == value
    assert model.build_command_line() == expected_args


def test_max_error_lines_rejects_other_strings() -> None:
    with pytest.raises(NamedTypeError):
        from_dict({"max-error-lines": "foo"}, RobotConfig)
