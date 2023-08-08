from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple, Union

import platformdirs

from .loader import ConfigType, DiscoverdBy, find_project_root, get_config_files_from_folder, get_default_config


def get_user_config_file(
    create: bool = True, verbose_callback: Optional[Callable[[str], None]] = None
) -> Optional[Path]:
    result = Path(platformdirs.user_config_dir("robotcode", appauthor=False), "robot.toml")
    if result.is_file():
        if verbose_callback:
            verbose_callback(f"Found user configuration file:\n    {result}")
        return result

    if not create:
        if verbose_callback:
            verbose_callback("User configuration file not found, but create is set to False.")
        return None

    if verbose_callback:
        verbose_callback(f"User configuration file not found, try to create it at:\n    {result}")

    get_default_config().save(result)

    return result


def get_config_files(
    paths: Optional[Sequence[Union[str, Path]]] = None,
    config_files: Optional[Sequence[Path]] = None,
    *,
    verbose_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[Sequence[Tuple[Path, ConfigType]], Optional[Path], DiscoverdBy]:
    root_folder, discovered_by = find_project_root(*(paths or []))

    if root_folder is None:
        root_folder = Path.cwd()
        if verbose_callback:
            verbose_callback(f"Cannot detect root folder. Use current folder '{root_folder}' as root.")

    if verbose_callback:
        verbose_callback(f"Found root at:\n    {root_folder} ({discovered_by.value})")

    if config_files:
        if verbose_callback:
            verbose_callback("Using config file:" + "\n    ".join([str(f) for f in config_files]))

        result: Sequence[Tuple[Path, ConfigType]] = [(f, ConfigType.CUSTOM_TOML) for f in config_files]
    else:
        result = get_config_files_from_folder(root_folder)

        if verbose_callback:
            if result:
                verbose_callback(
                    "Found configuration files:\n    " + "\n    ".join(str(f[0]) for f in result),
                )
            else:
                verbose_callback("No configuration files found.")

    user_config = get_user_config_file(verbose_callback=verbose_callback)

    return (
        [*([(user_config, ConfigType.USER_DEFAULT_CONFIG_TOML)] if user_config else []), *result],
        root_folder,
        discovered_by,
    )
