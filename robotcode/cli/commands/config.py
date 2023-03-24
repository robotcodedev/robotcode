from pathlib import Path
from typing import List, Union

import click

from robotcode.core.dataclasses import as_dict
from robotcode.plugin import ClickCommonConfig, pass_common_config
from robotcode.robot.config.loader import (
    find_project_root,
    load_config_from_path,
)

from ._common import get_config_files, print_dict


@click.group(
    invoke_without_command=False,
)
@pass_common_config
def config(
    common_config: ClickCommonConfig,
) -> Union[str, int, None]:
    """Commands to give informations about a robotframework configuration.

    By default the combined configuration is shown.
    """

    return 0


@config.command
@click.option(
    "-f", "--format", "format", type=click.Choice(["json", "toml"]), default="toml", help="Set the output format."
)
@click.option(
    "-s", "--single", "single", is_flag=True, default=False, help="Shows single files, not the combined config."
)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_common_config
def show(
    common_config: ClickCommonConfig,
    format: str,
    single: bool,
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows Robot Framework configuration."""

    config_files = get_config_files(common_config, paths)
    if not config_files:
        raise click.ClickException("Cannot find any configuration file. 😥")

    try:
        if single:
            for file, _ in config_files:
                config = load_config_from_path(file)
                click.secho(f"File: {file}")
                print_dict(as_dict(config, remove_defaults=True), format, common_config.colored_output)

            return 0

        config = load_config_from_path(*config_files)

        print_dict(as_dict(config, remove_defaults=True), format, common_config.colored_output)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    return 0


@config.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_common_config
def files(
    common_config: ClickCommonConfig,
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows Robot Framework configuration files."""

    config_files = get_config_files(common_config, paths)

    if config_files:
        for config_file, _ in config_files:
            click.echo(config_file)
        return 0

    click.secho("No configuration found. 😥", fg="red", err=True)

    return 1


@config.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_common_config
def root(
    common_config: ClickCommonConfig,
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows the root of the Robot Framework project."""

    root_folder, discovered_by = find_project_root(*(paths or []))

    if root_folder is None:
        raise click.ClickException("Cannot detect root folder for project. 😥")

    click.echo(f"{root_folder} (discovered by {discovered_by})")

    return 0
