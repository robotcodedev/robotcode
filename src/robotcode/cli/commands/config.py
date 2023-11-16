import dataclasses
import os
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from robotcode.core.dataclasses import encode_case_for_field_name
from robotcode.plugin import Application, OutputFormat, UnknownError, pass_application
from robotcode.plugin.manager import PluginManager
from robotcode.robot.config.loader import (
    DiscoverdBy,
    find_project_root,
    load_robot_config_from_path,
)
from robotcode.robot.config.model import LibDocProfile, RebotProfile, RobotConfig, RobotProfile, TestDocProfile
from robotcode.robot.config.utils import get_config_files


@click.group(
    invoke_without_command=False,
)
def config() -> None:
    """Shows information about the configuration."""


@config.command
@click.option(
    "-s", "--single", "single", is_flag=True, default=False, help="Shows single files, not the combined config."
)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def show(
    app: Application,
    single: bool,
    paths: List[Path],
) -> None:
    """\
    Shows the current configuration.

    Takes a list of PATHS or if no PATHS are given, takes the current working directory,
    to search for configuration files and prints the current configuration.

    \b
    Examples:
    ```
    robotcode config show
    robotcode config show tests/acceptance/first.robot
    robotcode --format json config show
    ```
    """
    try:
        config_files, _, _ = get_config_files(paths, app.config.config_files, verbose_callback=app.verbose)

        if single:
            for file, _ in config_files:
                config = load_robot_config_from_path(file)
                click.secho(f"File: {file}")
                app.print_data(config, remove_defaults=True, default_output_format=OutputFormat.TOML)

            return

        config = load_robot_config_from_path(*config_files)

        app.print_data(config, remove_defaults=True, default_output_format=OutputFormat.TOML)

    except (TypeError, ValueError, OSError) as e:
        raise UnknownError(str(e)) from e


@config.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@click.argument("user", type=bool, default=False)
@pass_application
def files(app: Application, paths: List[Path], user: bool = False) -> None:
    """\
    Search for configuration files and list them.

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
        config_files, _, discovered_by = get_config_files(paths, app.config.config_files, verbose_callback=app.verbose)

        result: Dict[str, Any] = {
            "files": [{"path": str(file), "type": type} for file, type in config_files],
        }

        messages = []
        if discovered_by == DiscoverdBy.NOT_FOUND:
            messages += ["Cannot detect root folder. 😥"]
        elif not config_files:
            messages += ["Cannot find any configuration file. 😥"]
        if messages:
            result["messages"] = messages

        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            for entry in result["files"]:
                app.echo(f'{entry["path"]} ({entry["type"].value})')
        else:
            app.print_data(result)

    except OSError as e:
        raise UnknownError(str(e)) from e


@config.command
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_application
def root(
    app: Application,
    paths: List[Path],
) -> None:
    """\
    Searches for the root folder of the project and prints them.

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

    if root_folder is None and (app.config.output_format is None or app.config.output_format == OutputFormat.TEXT):
        raise click.ClickException("Cannot detect root folder. 😥")

    result: Dict[str, Any] = {
        "root": {"path": str(root_folder) if root_folder is not None else None, "discoverdBy": discovered_by}
    }

    messages = []
    if discovered_by == DiscoverdBy.NOT_FOUND:
        messages += ["Cannot detect root folder. 😥"]

    if messages:
        result["messages"] = messages

    if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
        click.echo(f"{root_folder} (discovered by {discovered_by.value})")
    else:
        app.print_data(result)


@config.group
@pass_application
def info(app: Application) -> None:
    """Shows informations about possible configuration settings."""


def get_config_fields() -> Dict[str, Dict[str, str]]:
    result = {}
    for field in dataclasses.fields(RobotConfig):
        field_name_encoded = encode_case_for_field_name(RobotConfig, field)
        result[field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    for field in dataclasses.fields(RobotProfile):
        field_name_encoded = encode_case_for_field_name(RobotProfile, field)
        if field_name_encoded in result:
            continue

        result["[profile]." + field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    for field in dataclasses.fields(RebotProfile):
        field_name_encoded = encode_case_for_field_name(RebotProfile, field)
        result["rebot." + field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    for field in dataclasses.fields(LibDocProfile):
        field_name_encoded = encode_case_for_field_name(LibDocProfile, field)
        result["libdoc." + field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    for field in dataclasses.fields(TestDocProfile):
        field_name_encoded = encode_case_for_field_name(TestDocProfile, field)
        result["testdoc." + field_name_encoded] = {
            "type": str(field.type),
            "description": field.metadata.get("description", "").strip(),
        }

    for entry in PluginManager().config_classes:
        for s, cls in entry:
            if dataclasses.is_dataclass(cls):
                for field in dataclasses.fields(cls):
                    field_name_encoded = encode_case_for_field_name(TestDocProfile, field)
                    result[f"{s}." + field_name_encoded] = {
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

    result = []
    for n in name:
        for field in config_fields.keys():
            if fnmatchcase(field, n):
                result.append(field)

    if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
        app.echo_via_pager(os.linesep.join(result))
    else:
        app.print_data({"names": result})


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

    config_fields = [
        (field, value) for field, value in get_config_fields().items() if any(fnmatchcase(field, n) for n in name)
    ]

    if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
        output = ""
        for field, value in config_fields:
            output += f"## {field}\n\n"
            type = (
                value["type"]
                .replace("typing.", "")
                .replace("robotcode.robot.config.model.", "")
                .replace("NoneType", "None")
            )
            output += f"Type: {type}\n\n"
            output += value["description"] + "\n\n"

        app.echo_as_markdown(output)
    else:
        app.print_data(
            {
                "descriptions": [
                    {"name": field, "type": value["type"], "description": value["description"]}
                    for field, value in config_fields
                ]
            }
        )
