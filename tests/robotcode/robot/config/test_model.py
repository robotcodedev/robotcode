import json
from pathlib import Path
from typing import Any, Dict, List, get_type_hints

import pytest

from robotcode.core.utils.dataclasses import (
    NamedTypeError,
    TypeValidationError,
    as_dict,
    from_dict,
)
from robotcode.robot.config.model import LibDocProfile, RobotConfig


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


@pytest.mark.parametrize(
    ("value"),
    [
        ("dotted"),
        ("MyConsole.py:arg"),
    ],
)
def test_console_accepts_builtin_names_and_custom_consoles(value: str) -> None:
    model = from_dict({"console": value}, RobotConfig)
    assert model.console == value
    assert model.build_command_line() == ["--console", value]


def test_console_does_not_list_the_never_valid_skipped_value() -> None:
    console_type = str(get_type_hints(RobotConfig)["console"])

    assert "'dotted'" in console_type
    assert "skipped" not in console_type


def test_json_schema_does_not_list_skipped_as_console_value() -> None:
    schema_file = Path(__file__).parents[4] / "docs" / "public" / "schemas" / "robot.toml.json"
    schema = json.loads(schema_file.read_text(encoding="utf-8"))

    for owner in ("RobotConfig", "RobotProfile"):
        console = schema["definitions"][owner]["properties"]["console"]
        assert {"type": "string"} in console["anyOf"]
        assert "skipped" not in json.dumps(console["anyOf"])
    for owner in ("RebotProfile",):
        assert "console" not in schema["definitions"][owner]["properties"]


@pytest.mark.parametrize(
    ("data", "expected_args"),
    [
        # the command line uses the short option names: `-f` is `--format`, `-F` is `--docformat`
        ({"format": "MARKDOWN"}, ["-f", "MARKDOWN"]),
        ({"doc-format": "MARKDOWN"}, ["-F", "MARKDOWN"]),
    ],
)
def test_libdoc_accepts_markdown_formats(data: Dict[str, Any], expected_args: List[str]) -> None:
    model = from_dict(data, LibDocProfile)
    assert model.build_command_line() == expected_args

    config = from_dict({"libdoc": data}, RobotConfig)
    assert config.libdoc is not None
    assert config.libdoc.build_command_line() == expected_args
