from pathlib import Path
from typing import List, Union

import click

from robotcode.core.dataclasses import as_dict
from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.plugin.click_helper import add_options
from robotcode.robot.config.loader import (
    load_config_from_path,
)

from ._common import format_option, format_option_flat, get_config_files


@click.group(
    invoke_without_command=False,
)
@pass_application
def profiles(app: Application) -> Union[str, int, None]:
    """Commands to give informations about Robot Framework profiles."""

    return 0


@profiles.command
@add_options(format_option)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def show(
    app: Application,
    format: OutputFormat,
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows the given Robot Framework profile."""

    config_files = get_config_files(app.config, paths, app.verbose)
    if not config_files:
        raise click.ClickException("Cannot find any configuration file. 😥")

    try:
        profile = load_config_from_path(*config_files).combine_profiles(
            *(app.config.profiles or []), verbose_callback=app.verbose
        )

        app.print_dict(as_dict(profile, remove_defaults=True), format)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    return 0


@profiles.command
@add_options(format_option_flat)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def list(
    app: Application,
    format: OutputFormat,
    paths: List[Path],
) -> Union[str, int, None]:
    """List the defined profiles in the given Robot Framework configuration."""

    config_files = get_config_files(app.config, paths, app.verbose)
    if not config_files:
        raise click.ClickException("Cannot find any configuration file. 😥")

    try:
        config = load_config_from_path(*config_files)

        result = {"profiles": {k: {"description": v.description or ""} for k, v in (config.profiles or {}).items()}}

        if format == OutputFormat.FLAT:
            for profile, v in result["profiles"].items():
                click.secho(profile + " - " + v["description"])
        else:
            app.print_dict(result, format)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    return 0
