from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import click

from robotcode.plugin import CommonConfig, OutputFormat
from robotcode.plugin.click_helper import EnumChoice
from robotcode.robot.config.loader import (
    ConfigType,
    find_project_root,
    get_config_files_from_folder,
)

format_option = click.option(
    "-f",
    "--format",
    "format",
    type=EnumChoice(OutputFormat),
    default=OutputFormat.TOML,
    help="Set the output format.",
    show_default=True,
)

format_option_flat = click.option(
    "-f",
    "--format",
    "format",
    type=EnumChoice(OutputFormat),
    default=OutputFormat.FLAT,
    help="Set the output format.",
    show_default=True,
)


def get_config_files(
    common_config: CommonConfig, paths: List[Path], verbose_callback: Optional[Callable[[str], None]]
) -> Sequence[Tuple[Path, ConfigType]]:
    if common_config.config_file is not None:
        if verbose_callback:
            verbose_callback(f"Using config file: {common_config.config_file}")

        return [(common_config.config_file, ConfigType.CUSTOM_TOML)]

    root_folder, discovered_by = find_project_root(*(paths or []))

    if root_folder is None:
        raise click.ClickException("Cannot detect root folder for project. 😥")

    if verbose_callback:
        verbose_callback(f"Found project root at:\n    {root_folder} ({discovered_by.value})")

    result = get_config_files_from_folder(root_folder)

    if result:
        if verbose_callback:
            verbose_callback(
                "Found configuration files:\n    " + "\n    ".join(str(f[0]) for f in result),
            )

    return result
