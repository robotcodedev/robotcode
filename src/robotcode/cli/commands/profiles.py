from pathlib import Path
from typing import Any, Dict, List

import click
from robotcode.plugin import Application, OutputFormat, UnknownError, pass_application
from robotcode.robot.config.loader import (
    DiscoverdBy,
    load_config_from_path,
)
from robotcode.robot.config.utils import get_config_files


@click.group(
    invoke_without_command=False,
)
def profiles() -> None:
    """View profile informations."""


@profiles.command
@click.option(
    "-n", "--no-evaluate", "no_evaluate", is_flag=True, default=False, help="Don't evaluate expressions in the profile."
)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def show(
    app: Application,
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

        app.print_data(config, remove_defaults=True, default_output_format=OutputFormat.TOML)

    except (TypeError, ValueError, FileNotFoundError) as e:
        raise UnknownError(str(e)) from e


@profiles.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def list(
    app: Application,
    paths: List[Path],
) -> None:
    """List the defined profiles in the given Robot Framework configuration."""

    try:
        config_files, _, discovered_by = get_config_files(
            paths,
            app.config.config_files,
            verbose_callback=app.verbose,
            raise_on_error=app.config.output_format is None or app.config.output_format == OutputFormat.TEXT,
        )

        config = load_config_from_path(*config_files)
        selected_profiles = [
            k for k in config.select_profiles(*(app.config.profiles or []), verbose_callback=app.verbose).keys()
        ]

        result: Dict[str, Any] = {
            "profiles": [
                {"name": k, "description": v.description or "", "selected": True if k in selected_profiles else False}
                for k, v in (config.profiles or {}).items()
            ]
        }

        messages = []
        if discovered_by == DiscoverdBy.NOT_FOUND:
            messages += ["Cannot detect root folder. 😥"]
        elif not config_files:
            messages += ["Cannot find any configuration file. 😥"]
        elif not config.profiles:
            messages += ["No profiles defined."]
        if messages:
            result["messages"] = messages

        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            for v in result["profiles"]:
                app.echo(f'{"* " if v["selected"] else "  "}{v["name"]} {v["description"] if v["description"] else ""}')
        else:
            app.print_data(result)

    except (TypeError, ValueError, FileNotFoundError) as e:
        raise UnknownError(str(e)) from e
