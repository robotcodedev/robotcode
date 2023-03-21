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

    if "default_factory" not in kwargs:
        kwargs["default"] = None

    return dataclasses.field(*args, **kwargs)


@dataclass
class BaseProfile(ValidateMixin):
    """Base profile for Robot Framework."""

    @classmethod
    def _encode_case(cls, s: str) -> str:
        return s.replace("_", "-")

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return s.replace("-", "_")

    args: Optional[List[str]] = field(
        description="""\
            Extra arguments to be passed to Robot Framework

            Examples:
            ```toml
            args = ["-t", "abc"]
            ```
            """,
    )
    doc: Optional[str] = field(
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
    python_path: Optional[List[str]] = field(
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
    env: Optional[Dict[str, str]] = field(
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
    variables: Optional[Dict[str, Any]] = field(
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
    meta_data: Optional[Dict[str, Any]] = field(
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
    variable_files: Optional[List[str]] = field()

    paths: Optional[List[str]] = field(
        description="""\
            Paths to test data. If no paths are given at the command line this value is used.
            """,
    )
    output_dir: Optional[str] = field()
    output_file: Optional[str] = field()
    log_file: Optional[str] = field()
    debug_file: Optional[str] = field()
    log_level: Optional[str] = field()
    console: Union[ConsoleType, str, None] = field(default=None, description="Console output type.")
    mode: Optional[Mode] = field()
    languages: Optional[List[str]] = field()
    parsers: Optional[Dict[str, List[Any]]] = field()
    pre_run_modifiers: Optional[Dict[str, List[Any]]] = field()
    pre_rebot_modifiers: Optional[Dict[str, List[Any]]] = field()

    listeners: Optional[Dict[str, List[Any]]] = field()
    dry_run: Optional[bool] = field()


@dataclass
class Profile(BaseProfile):
    """Detachable Configuration for Robot Framework."""

    description: Optional[str] = field(description="Description of the profile.")
    detached: Optional[bool] = field(
        description="""\
            If the profile should be detached."
            Detached means it is not inherited from the main profile.
            """,
    )


@dataclass
class MainProfile(BaseProfile):
    """Configuration for Robot Framework."""

    default_profile: Union[str, List[str], None] = field(
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

    def get_profile(self, *names: str, verbose_callback: Callable[..., None] = None) -> BaseProfile:
        result = BaseProfile(
            **{f.name: new for f in dataclasses.fields(BaseProfile) if (new := getattr(self, f.name)) is not None}
        )

        for name in names:
            if name not in self.profiles:
                raise ValueError(f'Unknown profile "{name}".')

            if verbose_callback:
                verbose_callback(f'Using profile "{name}".')

            profile = self.profiles[name]

            for f in dataclasses.fields(profile):
                new = getattr(profile, f.name)
                if profile.detached:
                    setattr(result, f.name, new)
                elif new is not None:
                    old = getattr(result, f.name)
                    if old is not None and isinstance(old, list):
                        setattr(result, f.name, [*old, *new])
                    if old is not None and isinstance(old, dict):
                        setattr(result, f.name, {**old, **new})
                    else:
                        setattr(result, f.name, new)

        return result
