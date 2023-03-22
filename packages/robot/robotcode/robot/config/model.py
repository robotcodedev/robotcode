from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, get_type_hints

from robotcode.core.dataclasses import TypeValidationError, ValidateMixin, validate_types


class Mode(str, Enum):
    """Run mode for Robot Framework.

    - use `default` for normal execution
    - use `rpa` for RPA execution
    - use `norpa` for non-RPA execution

    Examples:
    ```toml
    mode = "rpa"
    ```
    """

    DEFAULT = "default"
    RPA = "rpa"
    NORPA = "norpa"

    def __str__(self) -> str:
        return self.value


class ConsoleType(str, Enum):
    """Console type for Robot Framework.

    - use `verbose` for verbose output
    - use `dotted` for dotted output
    - use `quiet` for quiet output
    - use `none` for no output

    Examples:
    ```toml
    console_type = "verbose"
    ```
    """

    VERBOSE = "verbose"
    DOTTED = "dotted"
    QUIET = "quiet"
    NONE = "none"

    def __str__(self) -> str:
        return self.value


def field(
    *args: Any,
    description: Optional[str] = None,
    robot_name: Optional[str] = None,
    robot_short_name: Optional[str] = None,
    robot_priority: Optional[int] = None,
    convert: Optional[Callable[[Any, Any], Any]] = None,
    **kwargs: Any,
) -> Any:
    metadata = kwargs.get("metadata", {})
    if description:
        metadata["description"] = "\n".join(line.strip() for line in description.splitlines())

    if convert is not None:
        metadata["convert"] = convert

    if robot_name is not None:
        metadata["robot_name"] = robot_name

    if robot_short_name is not None:
        metadata["robot_short_name"] = robot_short_name

    if robot_priority is not None:
        metadata["robot_priority"] = robot_priority

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
            Arguments to be passed to Robot Framework.

            Examples:
            ```toml
            args = ["-t", "abc"]
            ```
            """,
        robot_priority=1000,
    )
    name: Optional[str] = field(
        description="""\
            Set the name of the top level suite. By default the
            name is created based on the executed file or
            directory.

            Examples:
            ```toml
            name = "My Suite"
            ```
            """,
        robot_name="--doc",
        robot_short_name="-D",
        robot_priority=100,
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
        robot_name="--doc",
        robot_short_name="-D",
        robot_priority=100,
    )
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
        robot_name="--pythonpath",
        robot_short_name="-P",
        robot_priority=1,
    )
    env: Optional[Dict[str, str]] = field(
        description="""\
            Define environment variables to be set before tests.

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
        robot_name="--variable",
        robot_short_name="-v",
        robot_priority=300,
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

    paths: Union[str, List[str], None] = field(
        description="""\
            Paths to test data. If no paths are given at the command line this value is used.
            """,
        convert=lambda s, x: x if x is None else x if isinstance(x, list) else [x],
    )
    output_dir: Optional[str] = field(
        description="""\
            Where to create output files. The default is the
            directory where tests are run from and the given path
            is considered relative to that unless it is absolute.
            """,
        robot_name="--outputdir",
        robot_short_name="-d",
        robot_priority=50,
    )

    output_file: Optional[str] = field()
    log_file: Optional[str] = field()
    debug_file: Optional[str] = field()
    log_level: Optional[str] = field()
    console: Optional[ConsoleType] = field(
        default=None,
        description="""\
            How to report execution on the console.
            - `verbose`:  report every suite and test (default)
            - `dotted`:   only show `.` for passed test, `f` for
                          failed non-critical tests, and `F` for
                          failed critical tests
            - `quiet`:    no output except for errors and warnings
            - `none`:     no output whatsoever
            """,
        robot_name="--console",
        robot_priority=500,
    )
    mode: Optional[Mode] = field(
        description="""\
        Run mode for Robot Framework.

        - use `default` for normal execution
        - use `rpa` for RPA execution
        - use `norpa` for non-RPA execution

        Examples:
        ```toml
        mode = "rpa"
        ```
        """,
        robot_name="+value",
        robot_priority=0,
    )
    languages: Optional[List[str]] = field()
    parsers: Optional[Dict[str, List[Any]]] = field()
    pre_run_modifiers: Optional[Dict[str, List[Any]]] = field()
    pre_rebot_modifiers: Optional[Dict[str, List[Any]]] = field()

    listeners: Optional[Dict[str, List[Any]]] = field()
    dry_run: Optional[bool] = field()

    def build_robot_options(self) -> List[str]:
        """Build the arguments to pass to Robot Framework."""
        result = []

        sorted_fields = sorted(
            (f for f in dataclasses.fields(self) if f.metadata.get("robot_priority", -1) > -1),
            key=lambda f: f.metadata.get("robot_priority", 0),
        )

        def append_name(field: dataclasses.Field[Any]) -> None:
            if "robot_short_name" in field.metadata:
                result.append(field.metadata["robot_short_name"])
            elif "robot_name" in field.metadata:
                result.append(field.metadata["robot_name"])

        for field in sorted_fields:
            value = getattr(self, field.name)
            if value is None:
                continue

            if isinstance(value, list):
                for item in value:
                    append_name(field)
                    result.append(str(item))
            elif isinstance(value, dict):
                for key, item in value.items():
                    append_name(field)
                    result.append(f"{key}:{item}")
            else:
                if field.metadata.get("robot_name", None) == "+value":
                    if str(value) == "default":
                        continue

                    result.append(f"--{str(value)}")
                    continue

                append_name(field)
                result.append(str(value))

        return result


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

    extra_args: Optional[List[str]] = field(
        description="""\
            Extra arguments to be passed to Robot Framework

            Use this to append these paths to the inherited python path instead of overwriting them.

            Examples:
            ```toml
            extra-args = ["-t", "abc"]
            ```
            """,
    )

    extra_variables: Optional[Dict[str, Any]] = field(
        description="""\
            Set extra variables in the test data. Only scalar
            variables with string value are supported and name is
            given without `${}`

            Use this to append these variables to the inherited variables instead of overwriting them.

            Examples:
            ```toml
            [profiles.dummy.extra-variables]
            TEST_VAR = "test"
            SECRET = "password"
            ```
            """,
    )

    extra_env: Optional[Dict[str, str]] = field(
        description="""\
            Define extra environment variables to be set before tests.

            Examples:
            ```toml
            [profiles.dummy.env]
            TEST_VAR = "test"
            SECRET = "password"
            ```
            """,
    )

    extra_python_path: Optional[List[str]] = field(
        description="""\
            Extra additional locations (directories) where
            to search test libraries and other extensions when
            they are imported. Given path can also be a glob
            pattern matching multiple paths.

            Use this to append these paths to the inherited python path instead of overwriting them.

            Examples:
            ```toml
            extra-python-path = ["./lib", "./resources"]
            ```
            """,
    )


@dataclass
class RobotConfig(BaseProfile):
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

    @staticmethod
    def _verified_value(name: str, value: Any, types: Union[type, Tuple[type, ...]], target: Any) -> Any:
        errors = validate_types(types, value)
        if errors:
            raise TypeValidationError("Dataclass Type Validation Error", target=target, errors={name: errors})
        return value

    def get_profile(self, *names: str, verbose_callback: Callable[..., None] = None) -> BaseProfile:
        type_hints = get_type_hints(BaseProfile)

        result = BaseProfile(
            **{
                f.name: self._verified_value(f.name, new, type_hints[f.name], self)
                for f in dataclasses.fields(BaseProfile)
                if (new := getattr(self, f.name)) is not None
            }
        )

        base_field_names = [f.name for f in dataclasses.fields(BaseProfile)]

        for profile_name in names:
            if profile_name not in self.profiles:
                raise ValueError(f'Unknown profile "{profile_name}".')

            profile = self.profiles[profile_name]

            if verbose_callback:
                verbose_callback(f'Using profile "{profile_name}".')

            if profile.detached:
                result = BaseProfile()

            for f in dataclasses.fields(profile):
                if f.name.startswith("extra_"):
                    new = self._verified_value(f.name, getattr(profile, f.name), type_hints[f.name[6:]], profile)
                    if new is None:
                        continue

                    old = getattr(result, f.name[6:])
                    if old is None:
                        setattr(result, f.name[6:], new)
                    else:
                        if isinstance(old, dict):
                            setattr(result, f.name[6:], {**old, **new})
                        elif isinstance(old, list):
                            setattr(result, f.name[6:], [*old, *new])
                        elif isinstance(old, tuple):
                            setattr(result, f.name[6:], (*old, *new))
                        else:
                            setattr(result, f.name[6:], new)
                    continue

                if f.name not in base_field_names:
                    continue

                if getattr(profile, f"extra_{f.name}", None) is not None:
                    continue

                new = self._verified_value(f.name, getattr(profile, f.name), type_hints[f.name], profile)
                if new is not None:
                    setattr(result, f.name, new)

        return result
