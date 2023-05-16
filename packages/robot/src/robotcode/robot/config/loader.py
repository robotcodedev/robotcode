import sys
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple, Union

from robotcode.core.dataclasses import from_dict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


from .model import RobotConfig

PYPROJECT_TOML = "pyproject.toml"
ROBOT_TOML = "robot.toml"
LOCAL_ROBOT_TOML = ".robot.toml"


class DiscoverdBy(str, Enum):
    GIT = ".git directory"
    HG = "hg"
    PYPROJECT_TOML = PYPROJECT_TOML
    ROBOT_TOML = ROBOT_TOML
    LOCAL_ROBOT_TOML = LOCAL_ROBOT_TOML
    NOT_FOUND = "not found"


class ConfigType(str, Enum):
    PYPROJECT_TOML = PYPROJECT_TOML
    ROBOT_TOML = ROBOT_TOML
    LOCAL_ROBOT_TOML = LOCAL_ROBOT_TOML
    CUSTOM_TOML = ".toml"


class ConfigValueError(ValueError):
    def __init__(self, path: Path, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.path = path


class ConfigTypeError(TypeError):
    def __init__(self, path: Path, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.path = path


def loads_config_from_robot_toml(__s: str) -> RobotConfig:
    dict_data = tomllib.loads(__s)
    return from_dict(dict_data, RobotConfig)


def loads_config_from_pyproject_toml(__s: str) -> RobotConfig:
    dict_data = tomllib.loads(__s)

    return from_dict(dict_data.get("tool", {}).get("robot", {}), RobotConfig)


def _load_config_data_from_path(__path: Path) -> RobotConfig:
    try:
        if __path.name == PYPROJECT_TOML:
            return loads_config_from_pyproject_toml(__path.read_text("utf-8"))

        if __path.name == ROBOT_TOML or __path.name == LOCAL_ROBOT_TOML or __path.suffix == ".toml":
            return loads_config_from_robot_toml(__path.read_text("utf-8"))
        raise TypeError("Unknown config file type.")

    except ValueError as e:
        raise ConfigValueError(__path, f'Parsing "{__path}" failed: {e}') from e
    except TypeError as e:
        raise ConfigTypeError(__path, f'Parsing "{__path}" failed: {e}') from e


def load_config_from_path(*__paths: Union[Path, Tuple[Path, ConfigType]]) -> RobotConfig:
    result = RobotConfig()

    for __path in __paths:
        result.add_options(_load_config_data_from_path(__path if isinstance(__path, Path) else __path[0]))

    return result


def find_project_root(*sources: Union[str, Path]) -> Tuple[Optional[Path], DiscoverdBy]:
    if not sources:
        sources = (str(Path.cwd().resolve()),)

    path_srcs = [Path(Path.cwd(), src).resolve() for src in sources]

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
