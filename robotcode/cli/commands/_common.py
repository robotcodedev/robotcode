from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import click

from robotcode.core.dataclasses import as_json
from robotcode.plugin import ClickCommonConfig, ColoredOutput
from robotcode.robot.config.loader import (
    ConfigType,
    find_project_root,
    get_config_files_from_folder,
)


def print_dict(config: Dict[str, Any], format: str, color: ColoredOutput) -> None:
    text = None
    if format == "toml":
        try:
            import tomli_w

            text = tomli_w.dumps(config)
        except ImportError:
            click.secho("tomli-w is required to output toml.", fg="red", err=True)

            format = "json"

    if text is None:
        text = as_json(config, indent=True)

    if not text:
        return

    if color in [ColoredOutput.AUTO, ColoredOutput.YES]:
        try:
            from rich.console import Console
            from rich.syntax import Syntax

            Console().print(Syntax(text, format, background_color="default"))

            return
        except ImportError as e:
            if color == "yes":
                raise click.ClickException('Package "rich" is required to use colored output.') from e

    click.echo(text)

    return


def get_config_files(common_config: ClickCommonConfig, paths: List[Path]) -> Sequence[Tuple[Path, ConfigType]]:
    if common_config.config_file is not None:
        if common_config.verbose:
            click.secho(f"Using config file: {common_config.config_file}", fg="bright_black")

        return [(common_config.config_file, ConfigType.CUSTOM_TOML)]

    root_folder, discovered_by = find_project_root(*(paths or []))

    if root_folder is None:
        raise click.ClickException("Cannot detect root folder for project. 😥")

    if common_config.verbose:
        click.secho(f"Found project root at:\n    {root_folder} ({discovered_by})", fg="bright_black")

    result = get_config_files_from_folder(root_folder)

    if result:
        if common_config.verbose:
            click.secho(
                "Found configuration files:\n    " + "\n    ".join(str(f[0]) for f in result),
                fg="bright_black",
            )

    return result
