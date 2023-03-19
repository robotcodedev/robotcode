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
class BaseConfiguration(ValidateMixin):
    """Base configuration for Robot Framework."""

    @classmethod
    def _encode_case(cls, s: str) -> str:
        return s.replace("_", "-")

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return s.replace("-", "_")

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
    dry_run: Optional[bool] = None


@dataclass
class DetachableConfiguration(BaseConfiguration):
    """Detachable Configuration for Robot Framework."""

    detached: bool = False


@dataclass
class Configuration(BaseConfiguration):
    """Configuration for Robot Framework."""

    configurations: Dict[str, DetachableConfiguration] = field(
        default_factory=dict,
        metadata={"description": "Configurations for Robot Framework."},
    )


# if __name__ == "__main__":
#     import json
#     import pathlib

#     import pydantic

#     class Config:
#         title = "robot.toml"
#         description = "Configuration for Robot Framework."

#         @classmethod
#         def alias_generator(cls, string: str) -> str:
#             # this is the same as `alias_generator = to_camel` above
#             return string.replace("_", "-")

#     model = pydantic.dataclasses.create_pydantic_model_from_dataclass(Configuration, config=Config)  # type: ignore
#     schema = model.schema()

#     schema["$schema"] = "http://json-schema.org/draft-07/schema#"
#     schema[
#         "$id"
#     ] = "robotframework:https://raw.githubusercontent.com/d-biehl/robotcode/main/etc/robot.json"
#     schema["x-taplo-info"] = {
#         "authors": ["d-biehl (https://github.com/d-biehl)"],
#         "patterns": ["^(.*(/|\\\\)robot\\.toml|robot\\.toml)$"],
#     }
#     json_str = json.dumps(schema, indent=2, sort_keys=True)
#     pathlib.Path("etc", "robot.json").write_text(json_str, "utf-8")
