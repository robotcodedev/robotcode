import sys
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple, Type, TypeVar, Union

from robotcode.core.dataclasses import from_dict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


from .model import BaseOptions, RobotConfig

PYPROJECT_TOML = "pyproject.toml"
ROBOT_TOML = "robot.toml"
LOCAL_ROBOT_TOML = ".robot.toml"
USER_DEFAULT_CONFIG_TOML = "default config"


class DiscoverdBy(str, Enum):
    GIT = ".git directory"
    HG = "hg"
    PYPROJECT_TOML = "pyproject.toml (project file))"
    ROBOT_TOML = "robot.toml (project file)"
    LOCAL_ROBOT_TOML = ".robot.toml (local file)"
    USER_DEFAULT_CONFIG_TOML = "robot.toml (user default config)"
    NOT_FOUND = "not found"


class ConfigType(str, Enum):
    PYPROJECT_TOML = "pyproject.toml (project file))"
    ROBOT_TOML = "robot.toml (project file)"
    LOCAL_ROBOT_TOML = ".robot.toml (local file)"
    USER_DEFAULT_CONFIG_TOML = "robot.toml (user default config)"
    CUSTOM_TOML = ".toml (custom file)"


class ConfigValueError(ValueError):
    def __init__(self, path: Path, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.path = path


class ConfigTypeError(TypeError):
    def __init__(self, path: Path, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.path = path


_ConfigType = TypeVar("_ConfigType", bound=BaseOptions)


def load_robot_config_from_robot_toml_str(__s: str) -> RobotConfig:
    return load_config_from_robot_toml_str(RobotConfig, __s)


def load_config_from_robot_toml_str(
    config_type: Type[_ConfigType], __s: str, tool_name: Optional[str] = None
) -> _ConfigType:
    dict_data = tomllib.loads(__s)

    if tool_name:
        try:
            return from_dict(dict_data.get("tool", {}).get(tool_name, {}), config_type)
        except ValueError as e:
            raise ValueError(f"Reading [tool.{tool_name}] failed: {e}") from e
        except TypeError as e:
            raise TypeError(f"Reading [tool.{tool_name}] failed: {e}") from e

    return from_dict(dict_data, config_type)


def load_config_from_pyproject_toml_str(config_type: Type[_ConfigType], tool_name: str, __s: str) -> _ConfigType:
    dict_data = tomllib.loads(__s)

    return from_dict(dict_data.get("tool", {}).get(tool_name, {}), config_type)


def _load_config_data_from_path(
    config_type: Type[_ConfigType], tool_name: str, robot_toml_tool_name: Optional[str], __path: Path
) -> _ConfigType:
    try:
        if __path.name == PYPROJECT_TOML:
            return load_config_from_pyproject_toml_str(config_type, tool_name, __path.read_text("utf-8"))

        if __path.name == ROBOT_TOML or __path.name == LOCAL_ROBOT_TOML or __path.suffix == ".toml":
            return load_config_from_robot_toml_str(
                config_type, __path.read_text("utf-8"), tool_name=robot_toml_tool_name
            )
        raise TypeError("Unknown config file type.")

    except ValueError as e:
        raise ConfigValueError(__path, f'Parsing "{__path}" failed: {e}') from e
    except TypeError as e:
        raise ConfigTypeError(__path, f'Parsing "{__path}" failed: {e}') from e


def get_default_config() -> RobotConfig:
    result = RobotConfig()
    result.output_dir = "results"
    result.python_path = ["./lib", "./resources"]
    return result


def load_config_from_path(
    config_type: Type[_ConfigType],
    *__paths: Union[Path, Tuple[Path, ConfigType]],
    tool_name: str,
    robot_toml_tool_name: Optional[str] = None,
) -> _ConfigType:
    result = config_type()

    for __path in __paths:
        result.add_options(
            _load_config_data_from_path(
                config_type, tool_name, robot_toml_tool_name, __path if isinstance(__path, Path) else __path[0]
            )
        )

    return result


def load_robot_config_from_path(*__paths: Union[Path, Tuple[Path, ConfigType]]) -> RobotConfig:
    return load_config_from_path(RobotConfig, *__paths, tool_name="robot")


def find_project_root(*sources: Union[str, Path]) -> Tuple[Optional[Path], DiscoverdBy]:
    if not sources:
        sources = (str(Path.cwd().absolute()),)

    path_srcs = [Path(Path.cwd(), src).absolute() for src in sources]

    src_parents = [list(path.parents) + ([path] if path.is_dir() else []) for path in path_srcs]

    common_base = max(
        set.intersection(*(set(parents) for parents in src_parents)),
        key=lambda path: path.parts,
    )

    for directory in (common_base, *common_base.parents):
        if (directory / LOCAL_ROBOT_TOML).is_file():
            return directory, DiscoverdBy.LOCAL_ROBOT_TOML

        if (directory / ROBOT_TOML).is_file():
            return directory, DiscoverdBy.ROBOT_TOML

        if (directory / PYPROJECT_TOML).is_file():
            return directory, DiscoverdBy.PYPROJECT_TOML

        if (directory / ".git").exists():
            return directory, DiscoverdBy.GIT

        if (directory / ".hg").is_dir():
            return directory, DiscoverdBy.HG

    return None, DiscoverdBy.NOT_FOUND


def get_config_files_from_folder(folder: Path) -> Sequence[Tuple[Path, ConfigType]]:
    result = []

    pyproject_toml = folder / PYPROJECT_TOML
    if pyproject_toml.is_file():
        result.append((pyproject_toml, ConfigType.PYPROJECT_TOML))

    robot_toml = folder / ROBOT_TOML
    if robot_toml.is_file():
        result.append((robot_toml, ConfigType.ROBOT_TOML))

    local_robot_toml = folder / LOCAL_ROBOT_TOML
    if local_robot_toml.is_file():
        result.append((local_robot_toml, ConfigType.LOCAL_ROBOT_TOML))

    return result
