from pathlib import Path
from typing import List, Union

import click

from robotcode.core.dataclasses import as_dict
from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.plugin.click_helper import add_options
from robotcode.robot.config.loader import (
    find_project_root,
    load_config_from_path,
)

from ._common import format_option, get_config_files


@click.group(
    invoke_without_command=False,
)
@pass_application
def config(
    app: Application,
) -> Union[str, int, None]:
    """Commands to give informations about a robotframework configuration.

    By default the combined configuration is shown.
    """

    return 0


@config.command
@add_options(format_option)
@click.option(
    "-s", "--single", "single", is_flag=True, default=False, help="Shows single files, not the combined config."
)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def show(
    app: Application,
    format: OutputFormat,
    single: bool,
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows Robot Framework configuration."""

    config_files = get_config_files(app.config, paths, app.verbose)
    if not config_files:
        raise click.ClickException("Cannot find any configuration file. 😥")

    try:
        if single:
            for file, _ in config_files:
                config = load_config_from_path(file)
                click.secho(f"File: {file}")
                app.print_dict(as_dict(config, remove_defaults=True), format)

            return 0

        config = load_config_from_path(*config_files)

        app.print_dict(as_dict(config, remove_defaults=True), format)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    return 0


@config.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def files(
    app: Application,
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows Robot Framework configuration files."""

    config_files = get_config_files(app.config, paths, app.verbose)

    if config_files:
        for config_file, _ in config_files:
            click.echo(config_file)
        return 0

    raise click.ClickException("No configuration found. 😥")


@config.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def root(
    app: Application,
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows the root of the Robot Framework project."""

    root_folder, discovered_by = find_project_root(*(paths or []))

    if root_folder is None:
        raise click.ClickException("Cannot detect root folder for project. 😥")

    click.echo(f"{root_folder} (discovered by {discovered_by})")

    return 0
