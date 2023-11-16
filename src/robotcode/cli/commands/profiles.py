from pathlib import Path
from typing import Any, Dict, List

import click
from robotcode.plugin import Application, OutputFormat, UnknownError, pass_application
from robotcode.robot.config.loader import (
    DiscoverdBy,
    load_robot_config_from_path,
)
from robotcode.robot.config.model import EvaluationError, RobotProfile
from robotcode.robot.config.utils import get_config_files


@click.group(
    invoke_without_command=False,
)
def profiles() -> None:
    """Shows information on defined profiles."""


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
    """Shows the given profile configuration."""
    try:
        config_files, _, _ = get_config_files(paths, app.config.config_files, verbose_callback=app.verbose)

        config = load_robot_config_from_path(*config_files).combine_profiles(
            *(app.config.profiles or []), verbose_callback=app.verbose
        )

        if not no_evaluate:
            config = config.evaluated()

        app.print_data(config, remove_defaults=True, default_output_format=OutputFormat.TOML)

    except (TypeError, ValueError, OSError) as e:
        raise UnknownError(str(e)) from e


@profiles.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def list(
    app: Application,
    paths: List[Path],
) -> None:
    """Lists the defined profiles in the current configuration."""

    try:
        config_files, _, discovered_by = get_config_files(
            paths,
            app.config.config_files,
            verbose_callback=app.verbose,
        )

        config = load_robot_config_from_path(*config_files)
        selected_profiles = [
            k for k in config.select_profiles(*(app.config.profiles or []), verbose_callback=app.verbose).keys()
        ]

        def check_enabled(name: str, profile: RobotProfile) -> bool:
            try:
                return profile.enabled is None or bool(profile.enabled)
            except EvaluationError as e:
                raise ValueError(f"Cannot evaluate profile '{name}'.enabled: {e}") from e

        result: Dict[str, Any] = {
            "profiles": [
                {
                    "name": k,
                    "enabled": check_enabled(k, v),
                    "description": v.description or "",
                    "selected": True if k in selected_profiles else False,
                }
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
                for k in ["name", "description"]:
                    lines = v[k].splitlines()
                    v[k] = " ".join(lines[:1]) + (" ..." if len(lines) > 1 else "")

            header = ""
            max_name = max(0, len("Name"), *(len(profile["name"]) for profile in result["profiles"]))
            max_description = max(
                0, len("Description"), *(len(profile["description"]) for profile in result["profiles"])
            )
            header += (
                f'| Active | Selected | Enabled | Name{(max_name-len("Name"))*" "} '
                f'| Description{(max_description-len("Description"))*" "} |\n'
            )
            header += f"|:------:|:--------:|:-------:|:{max_name*'-'}-|:{max_description*'-'}-|\n"
            for selected, enabled, name, description in (
                (v["selected"], v["enabled"], v["name"], v["description"]) for v in result["profiles"]
            ):
                header += (
                    f'|   {"*" if selected and enabled else " "}    '
                    f'|    {"*" if selected else " "}     '
                    f'|    {"*" if enabled else " "}    '
                    f'| {name}{(max_name-len(name))*" "} '
                    f'| {description if description else ""}{(max_description-len(description))*" "} |\n'
                )

            app.echo_as_markdown(header)
        else:
            app.print_data(result)

    except (TypeError, ValueError, OSError) as e:
        raise UnknownError(str(e)) from e
