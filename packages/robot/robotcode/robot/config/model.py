from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from robotcode.core.dataclasses import ValidateMixin


class Mode(str, Enum):
    """Run mode for Robot Framework."""

    DEFAULT = "default"
    RPA = "rpa"
    NORPA = "norpa"


class ConsoleType(str, Enum):
    """Run mode for Robot Framework."""

    VERBOSE = "verbose"
    DOTTED = "dotted"
    QUIET = "quiet"
    NONE = "none"


def field(
    *args: Any,
    description: Optional[str] = None,
    convert: Optional[Callable[[Any, Any], Any]] = None,
    **kwargs: Any,
) -> Any:
    metadata = kwargs.get("metadata", {})
    if description:
        metadata["description"] = "\n".join(line.strip() for line in description.splitlines())

    if convert is not None:
        metadata["convert"] = convert

    if metadata:
        kwargs["metadata"] = metadata
    return dataclasses.field(*args, **kwargs)


@dataclass
class BaseProfile(ValidateMixin):
    """Base configuration for Robot Framework."""

    @classmethod
    def _encode_case(cls, s: str) -> str:
        return s.replace("_", "-")

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return s.replace("-", "_")

    args: List[str] = field(
        default_factory=list,
        description="""\
            Extra arguments to be passed to Robot Framework

            Examples:
            ```toml
            args = ["-t", "abc"]
            ```
            """,
    )
    doc: Optional[str] = field(
        default=None,
        description="""\
            Set the documentation of the top level suite.
            Simple formatting is supported (e.g. *bold*). If the
            documentation contains spaces, it must be quoted.
            If the value is path to an existing file, actual
            documentation is read from that file.

            Examples:
            ```toml
            doc = \"\"\"Very *good* example

            This is a second paragraph.
            \"\"\"
            ```
            """,
    )
    """Arguments to be passed to Robot Framework"""
    python_path: List[str] = field(
        default_factory=list,
        description="""\
            Additional locations directories where
            to search test libraries and other extensions when
            they are imported. Given path can also be a glob
            pattern matching multiple paths.

            Examples:
            ```toml
            python-path = ["./lib", "./resources"]
            ```
            """,
    )
    env: Dict[str, str] = field(
        default_factory=dict,
        description="""\
            Set variables in the test data. Only scalar
            variables with string value are supported and name is
            given without `${}`

            Examples:
            ```toml
            [env]
            TEST_VAR = "test"
            SECRET = "password"
            ```
            """,
    )
    variables: Dict[str, Any] = field(
        default_factory=dict,
        description="""\
            Set variables in the test data. Only scalar
            variables with string value are supported and name is
            given without `${}`

            Examples:
            ```toml
            [variables]
            TEST_VAR = "test"
            SECRET = "password"
            ```
            """,
    )
    meta_data: Dict[str, Any] = field(
        default_factory=dict,
        description="""\
            Set metadata of the top level suite. Value can
            contain formatting and be read from a file similarly

            Examples:
            ```toml
            [meta-data]
            Version = "1.2"
            Release = "release.txt"
            ```
            """,
    )
    variable_files: List[str] = field(default_factory=list)

    def __ensure_list(self, x: Union[str, List[str], None]) -> Optional[List[str]]:
        if x is None:
            return None
        return [x] if isinstance(x, str) else x

    paths: Union[str, List[str], None] = field(
        default=None,
        description="""\
            Paths to test data. If no paths are given at the command line this value is used.
            """,
        convert=__ensure_list,
    )
    output_dir: Optional[str] = None
    output_file: Optional[str] = None
    log_file: Optional[str] = None
    debug_file: Optional[str] = None
    log_level: Optional[str] = None
    console: Union[ConsoleType, str, None] = field(default=None, description="Console output type.")
    mode: Optional[Mode] = None
    languages: List[str] = field(default_factory=list)
    parsers: Dict[str, List[Any]] = field(default_factory=dict)
    pre_run_modifiers: Dict[str, List[Any]] = field(default_factory=dict)
    pre_rebot_modifiers: Dict[str, List[Any]] = field(default_factory=dict)

    listeners: Dict[str, List[Any]] = field(default_factory=dict)
    dry_run: Optional[bool] = None


@dataclass
class Profile(BaseProfile):
    """Detachable Configuration for Robot Framework."""

    description: Optional[str] = field(default=None, description="Description of the profile.")
    detached: bool = field(
        default=False,
        description="""\
            If the profile should be detached."
            Detached means it is not inherited from the main profile.
            """,
    )


@dataclass
class MainProfile(BaseProfile):
    """Configuration for Robot Framework."""

    default_profile: Union[str, List[str], None] = field(
        default=None,
        description="""\
            Selects the Default profile if no profile is given at command line.

            Examples:
            ```toml
            default_profile = "default"
            ```

            ```toml
            default_profile = ["default", "Firefox"]
            ```
            """,
    )
    profiles: Dict[str, Profile] = field(
        default_factory=dict,
        metadata={"description": "Execution Profiles."},
    )
