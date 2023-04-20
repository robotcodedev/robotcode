import dataclasses
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional

import click
from robotcode.core.dataclasses import as_dict, encode_case
from robotcode.plugin import Application, OutputFormat, UnknownError, pass_application
from robotcode.plugin.click_helper.helper import add_options
from robotcode.robot.config.loader import (
    find_project_root,
    load_config_from_path,
)
from robotcode.robot.config.model import LibDocProfile, RebotProfile, RobotConfig, TestDocProfile
from robotcode.robot.config.utils import get_config_files

from ._common import format_option


@click.group(
    invoke_without_command=False,
)
@pass_application
def config(
    app: Application,
) -> None:
    """\
    View configuration information.
    """


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
) -> None:
    """\
    Shows the Robot Framework configuration.

    Takes a list of PATHS or if no PATHS are given, takes the current working directory,
    to search for configuration files and prints the current configuration.

    \b
    Examples:
    ```
    robotcode config show
    robotcode config show tests/acceptance/first.robot
    robotcode config show --format json
    ```
    """

    config_files, _, _ = get_config_files(paths, app.config.config_files, verbose_callback=app.verbose)

    try:
        if single:
            for file, _ in config_files:
                config = load_config_from_path(file)
                click.secho(f"File: {file}")
                app.print_dict(as_dict(config, remove_defaults=True), format)

            return

        config = load_config_from_path(*config_files)

        app.print_dict(as_dict(config, remove_defaults=True), format)

    except (TypeError, ValueError) as e:
        raise UnknownError(str(e)) from e


@config.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def files(
    app: Application,
    paths: List[Path],
) -> None:
    """\
    Shows Robot Framework configuration files.

    Takes a list of PATHS or if no PATHS are given, takes the current working directory,
    to search for configuration files and prints them.

    \b
    Examples:

    ```
    robotcode config files
    robotcode config files tests/acceptance/first.robot
    ```
    """

    try:
        config_files, _, _ = get_config_files(paths, app.config.config_files, verbose_callback=app.verbose)

        for config_file, _ in config_files:
            click.echo(config_file)

    except FileNotFoundError as e:
        raise UnknownError(str(e)) from e


@config.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def root(
    app: Application,
    paths: List[Path],
) -> None:
    """\
    Shows the root of the Robot Framework project.

    Takes a list of PATHS or if no PATHS are given, takes the current working directory,
    to search for the root of the project and prints this.

    \b
    Examples:

    ```
    robotcode config root
    robotcode config root tests/acceptance/first.robot
    ```
    """

    root_folder, discovered_by = find_project_root(*(paths or []))

    if root_folder is None:
        raise click.ClickException("Cannot detect root folder for project. 😥")

    click.echo(f"{root_folder} (discovered by {discovered_by})")


@config.group
@pass_application
def info(app: Application) -> None:
    """Shows informations about possible configuration settings."""


def get_config_fields() -> Dict[str, Dict[str, str]]:
    result = {}
    for field in dataclasses.fields(RobotConfig):
        field_name_encoded = encode_case(RobotConfig, field)
        result[field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    for field in dataclasses.fields(RebotProfile):
        field_name_encoded = encode_case(RebotProfile, field)
        result["rebot." + field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    for field in dataclasses.fields(LibDocProfile):
        field_name_encoded = encode_case(LibDocProfile, field)
        result["libdoc." + field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    for field in dataclasses.fields(TestDocProfile):
        field_name_encoded = encode_case(TestDocProfile, field)
        result["testdoc." + field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    return {k: v for k, v in sorted(result.items(), key=lambda item: item[0])}


@info.command()
@click.argument("name", type=str, nargs=-1)
@pass_application
def list(app: Application, name: Optional[List[str]] = None) -> None:
    """\
    Lists all possible configuration settings.

    If NAME is given searches for given name. Wildcards are supported.

    \b
    Examples:

    ```
    robotcode config info list
    robotcode config info list rebot.*
    robotcode config info list *tag*
    ```
    """
    if not name:
        name = ["*"]

    config_fields = get_config_fields()

    for n in name:
        for field in config_fields.keys():
            if fnmatch.fnmatchcase(field, n):
                app.echo(field)


@info.command()
@click.argument("name", type=str, nargs=-1)
@pass_application
def desc(app: Application, name: Optional[List[str]] = None) -> None:
    """\
    Shows the description of the specified configuration settings.

    If no NAME is given shows the description of all possible configuration settings.
    Wildcards are supported.

    \b
    Examples:

    ```
    robotcode config info desc
    robotcode config info desc python-path
    robotcode config info desc rebot.*
    robotcode config info desc *tag*
    ```
    """
    if not name:
        name = ["*"]

    config_fields = get_config_fields()

    for n in name:
        for field, value in config_fields.items():
            if fnmatch.fnmatchcase(field, n):
                output = f"## {field}\n\n"
                output += f"Type: {value['type']}\n\n"
                output += value["description"] + "\n\n"

                app.echo_as_markdown(output)
