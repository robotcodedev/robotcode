from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple, Union

from .loader import (
    ConfigType,
    DiscoverdBy,
    find_project_root,
    get_config_files_from_folder,
)


def get_config_files(
    paths: Optional[Sequence[Union[str, Path]]] = None,
    config_files: Optional[Sequence[Path]] = None,
    *,
    raise_on_error: bool = True,
    verbose_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[Sequence[Tuple[Path, ConfigType]], Optional[Path], DiscoverdBy]:
    root_folder, discovered_by = find_project_root(*(paths or []))

    if root_folder is None:
        if raise_on_error:
            raise FileNotFoundError("Cannot detect root folder. 😥")
        if verbose_callback:
            verbose_callback("Cannot detect root folder. 😥")
        return [], None, DiscoverdBy.NOT_FOUND

    if verbose_callback:
        verbose_callback(f"Found root at:\n    {root_folder} ({discovered_by.value})")

    if config_files:
        if verbose_callback:
            verbose_callback("Using config file:" + "\n    ".join(str(config_files)))

        return [(f, ConfigType.CUSTOM_TOML) for f in config_files], root_folder, discovered_by

    result = get_config_files_from_folder(root_folder)

    if not result and raise_on_error:
        raise FileNotFoundError("Cannot find any configuration file. 😥")

    if verbose_callback:
        if result:
            verbose_callback(
                "Found configuration files:\n    " + "\n    ".join(str(f[0]) for f in result),
            )
        else:
            verbose_callback("No configuration files found.")

    return result, root_folder, discovered_by
