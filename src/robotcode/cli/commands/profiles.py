from pathlib import Path
from typing import List

import click
from robotcode.core.dataclasses import as_dict
from robotcode.plugin import Application, OutputFormat, UnknownError, pass_application
from robotcode.plugin.click_helper.helper import add_options
from robotcode.robot.config.loader import (
    load_config_from_path,
)
from robotcode.robot.config.utils import get_config_files

from ._common import format_option, format_option_flat


@click.group(
    invoke_without_command=False,
)
@pass_application
def profiles(app: Application) -> None:
    """View profile informations."""


@profiles.command
@add_options(format_option)
@click.option(
    "-n", "--no-evaluate", "no_evaluate", is_flag=True, default=False, help="Don't evaluate expressions in the profile."
)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def show(
    app: Application,
    format: OutputFormat,
    no_evaluate: bool,
    paths: List[Path],
) -> None:
    """Shows the given Robot Framework profile."""
    try:
        config_files, _, _ = get_config_files(paths, app.config.config_files, verbose_callback=app.verbose)

        config = load_config_from_path(*config_files).combine_profiles(
            *(app.config.profiles or []), verbose_callback=app.verbose
        )

        if not no_evaluate:
            config = config.evaluated()

        app.print_dict(as_dict(config, remove_defaults=True), format)

    except (TypeError, ValueError, FileNotFoundError) as e:
        raise UnknownError(str(e)) from e


@profiles.command
@add_options(format_option_flat)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def list(
    app: Application,
    format: OutputFormat,
    paths: List[Path],
) -> None:
    """List the defined profiles in the given Robot Framework configuration."""

    try:
        config_files, _, _ = get_config_files(paths, app.config.config_files, verbose_callback=app.verbose)

        config = load_config_from_path(*config_files)
        selected_profiles = [
            k for k in config.select_profiles(*(app.config.profiles or []), verbose_callback=app.verbose).keys()
        ]

        result = {
            "profiles": {
                k: {"description": v.description or "", "selected": True if k in selected_profiles else False}
                for k, v in (config.profiles or {}).items()
            }
        }

        if format == OutputFormat.FLAT:
            for profile, v in result["profiles"].items():
                click.secho(
                    f'{"* " if v["selected"] else "  "}{profile} {v["description"] if v["description"] else ""}'
                )
        else:
            app.print_dict(result, format)

    except (TypeError, ValueError, FileNotFoundError) as e:
        raise UnknownError(str(e)) from e
