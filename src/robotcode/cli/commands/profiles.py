from pathlib import Path
from typing import Any, Dict, List, cast

import click

from robotcode.plugin import (
    Application,
    OutputFormat,
    UnknownError,
    pass_application,
)
from robotcode.robot.config.loader import (
    DiscoverdBy,
    load_robot_config_from_path,
)
from robotcode.robot.config.utils import get_config_files


@click.group(invoke_without_command=False)
def profiles() -> None:
    """Shows information on defined profiles."""


@profiles.command
@click.option(
    "-n",
    "--no-evaluate",
    "no_evaluate",
    is_flag=True,
    default=False,
    help="Don't evaluate expressions in the profile.",
)
@click.argument(
    "paths",
    type=click.Path(exists=True, path_type=Path),
    nargs=-1,
    required=False,
)
@pass_application
def show(app: Application, no_evaluate: bool, paths: List[Path]) -> None:
    """Shows the given profile configuration."""
    try:
        config_files, _, _ = get_config_files(
            paths, app.config.config_files, root_folder=app.config.root, verbose_callback=app.verbose
        )

        config = load_robot_config_from_path(*config_files, verbose_callback=app.verbose).combine_profiles(
            *(app.config.profiles or []), verbose_callback=app.verbose, error_callback=app.error
        )

        if not no_evaluate:
            config = config.evaluated_with_env(verbose_callback=app.verbose, error_callback=app.error)

        app.print_data(
            config,
            remove_defaults=True,
            default_output_format=OutputFormat.TOML,
        )

    except (TypeError, ValueError, OSError) as e:
        raise UnknownError(str(e)) from e


@profiles.command
@click.argument(
    "paths",
    type=click.Path(exists=True, path_type=Path),
    nargs=-1,
    required=False,
)
@click.option("-h", "--show-hidden", is_flag=True, default=False, help="Show hidden profiles.")
@click.option("-sp", "--sort-by-precedence", is_flag=True, default=False, help="Sort by precedence.")
@pass_application
def list(app: Application, paths: List[Path], show_hidden: bool = False, sort_by_precedence: bool = False) -> None:
    """Lists the defined profiles in the current configuration."""

    try:
        config_files, _, discovered_by = get_config_files(
            paths,
            app.config.config_files,
            root_folder=app.config.root,
            no_vcs=app.config.no_vcs,
            verbose_callback=app.verbose,
        )

        config = load_robot_config_from_path(*config_files, verbose_callback=app.verbose)

        _, selected_profiles, enabled_names = config.combine_profiles_ex(
            *(app.config.profiles or []), verbose_callback=app.verbose, error_callback=app.error
        )

        selected_names = [k for k in selected_profiles.keys()]

        result: Dict[str, Any] = {
            "profiles": sorted(
                [
                    {
                        "name": k,
                        "enabled": k in enabled_names,
                        "description": v.description or "",
                        "selected": True if k in selected_names else False,
                        "precedence": v.precedence,
                    }
                    for k, v in (config.profiles or {}).items()
                    if show_hidden or not k.startswith("_") and not v.hidden
                ],
                key=(
                    (lambda v: cast(Any, str(v.get("name", ""))))
                    if not sort_by_precedence
                    else (lambda v: cast(Any, v.get("precedence", 0) or 0))
                ),
            ),
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
            max_name = max(
                0,
                len("Name"),
                *(len(profile["name"]) for profile in result["profiles"]),
            )
            max_description = max(
                0,
                len("Description"),
                *(len(profile["description"]) for profile in result["profiles"]),
            )
            header += (
                f'| Active | Selected | Enabled | Precedence | Name{(max_name - len("Name")) * " "} '
                f'| Description{(max_description - len("Description")) * " "} |\n'
            )
            header += f"|:------:|:------:|:--------:|:-------:|:{max_name * '-'}-|:{max_description * '-'}-|\n"
            for selected_profiles, enabled, name, description, precedence in (
                (v["selected"], v["enabled"], v["name"], v["description"], v["precedence"]) for v in result["profiles"]
            ):
                header += (
                    f'|   {"*" if selected_profiles and enabled else " "}    '
                    f'|    {"*" if selected_profiles else " "}     '
                    f'|    {"*" if enabled else " "}    '
                    f'|    {precedence if precedence else " "}    '
                    f'| {name}{(max_name - len(name)) * " "} '
                    f'| {description if description else ""}{(max_description - len(description)) * " "} |\n'
                )

            app.echo_as_markdown(header)
        else:
            app.print_data(result)

    except (TypeError, ValueError, OSError) as e:
        raise UnknownError(str(e)) from e
