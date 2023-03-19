from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from robotcode.core.dataclasses import ValidateMixin


class Mode(Enum):
    """Run mode for Robot Framework."""

    DEFAULT = "default"
    RPA = "rpa"
    NORPA = "norpa"


@dataclass
class BaseConfig(ValidateMixin):
    """Base configuration for Robot Framework."""

    args: List[str] = field(
        default_factory=list,
        metadata={
            "description": """\
Extra arguments to be passed to Robot Framework

Examples:
```toml
args = ["-t", "abc"]
```
"""
        },
    )
    documentation: Optional[str] = field(default=None, metadata={"description": "Documentation for the test suite."})
    """Arguments to be passed to Robot Framework"""
    python_path: List[str] = field(
        default_factory=list,
        metadata={
            "description": """\
Additional locations directories where
to search test libraries and other extensions when
they are imported. Given path can also be a glob
pattern matching multiple paths.

Examples:
```toml
python_path = ["./lib", "./resources"]
```
""",
        },
    )
    env: Dict[str, str] = field(
        default_factory=dict,
        metadata={
            "description": """\
Environment variables to be set before running tests.

Examples:
```toml
[env]
TEST_VAR = "test"
SECRET = "password"
```
"""
        },
    )
    variables: Dict[str, Any] = field(default_factory=dict)
    variable_files: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    output_dir: Optional[str] = None
    output_file: Optional[str] = None
    log_file: Optional[str] = None
    debug_file: Optional[str] = None
    log_level: Optional[str] = None
    console: Optional[str] = None
    mode: Optional[Mode] = None
    meta_data: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    parsers: Dict[str, List[Any]] = field(default_factory=dict)
    pre_run_modifiers: Dict[str, List[Any]] = field(default_factory=dict)
    pre_rebot_modifiers: Dict[str, List[Any]] = field(default_factory=dict)

    listeners: Dict[str, List[Any]] = field(default_factory=dict)


@dataclass
class EnvironmentConfig(BaseConfig):
    detached: bool = False


@dataclass
class RobotConfig(BaseConfig):
    configs: Dict[str, EnvironmentConfig] = field(default_factory=dict)


# if __name__ == "__main__":
#     import pathlib

#     from pydantic import schema_json_of

#     json = schema_json_of(RobotConfig, by_alias=False, indent=2)
#     # TODO add $id and $schema
#     # json["$id"] = "https://json.schemastore.org/robot.schema.json"
#     # json["$schema"] = "http://json-schema.org/draft-07/schema#"
#     pathlib.Path("etc", "robot.json").write_text(json, "utf-8")
