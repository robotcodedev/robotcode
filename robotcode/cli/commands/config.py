import sys
from pathlib import Path
from typing import List, Optional, Union

import click

from robotcode.core.dataclasses import as_dict, as_json
from robotcode.plugin import CommonConfig, pass_common_config
from robotcode.robot.config.loader import find_project_root, get_config_files_from_folder, load_config_from_path
from robotcode.robot.config.model import RobotConfig

if sys.version_info >= (3, 11):
    pass
else:
    pass


@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "auto_envvar_prefix": "ROBOTCODE"},
    invoke_without_command=False,
)
@click.pass_context
@pass_common_config
def config(
    common_config: CommonConfig,
    ctx: click.Context,
) -> Union[str, int, None]:
    """Commands to give informations about a robotframework configuration.

    By default the combined configuration is shown.
    """

    return 0


def print_config(config: RobotConfig, format: str, color: str) -> int:
    text = None
    if format == "toml":
        try:
            import tomli_w

            text = tomli_w.dumps(as_dict(config, remove_defaults=True))
        except ImportError:
            click.secho("tomli-w is required to output toml.", fg="red", err=True)

            format = "json"

    if text is None:
        text = as_json(config, indent=True)

    if color in ["auto", "yes"]:
        try:
            from rich.console import Console
            from rich.syntax import Syntax

            Console().print(Syntax(text, format, background_color="default"))

            return 0
        except ImportError:
            if color == "yes":
                click.secho("rich is required to use colors.", fg="red", err=True)
                return 1
            pass

    click.echo(text)

    return 0


@config.command
@click.option(
    "-f", "--format", "format", type=click.Choice(["json", "toml"]), default="toml", help="Set the output format."
)
@click.option(
    "-c",
    "--color",
    "color",
    type=click.Choice(["auto", "yes", "no"]),
    default="auto",
    help="Enables/disables colored output.",
)
@click.option(
    "-s", "--single", "single", is_flag=True, default=False, help="Shows single files, not the combined config."
)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@click.pass_context
@pass_common_config
def show(
    common_config: CommonConfig,
    ctx: click.Context,
    format: str,
    color: str,
    single: bool,
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows robotframework configuration files."""

    root_folder, discovered_by = find_project_root(*(paths or []))
    if common_config.verbose:
        click.secho(f"Found project root at:\n    {root_folder} ({discovered_by})", fg="bright_black")

    config: Optional[RobotConfig] = None

    if root_folder is not None:
        config_files = get_config_files_from_folder(root_folder)
        if config_files:
            try:
                if single:
                    for file, _ in config_files:
                        config = load_config_from_path(file)
                        click.secho(f"File: {file}")
                        if print_config(config, format, color):
                            return 1
                    return 0

                if common_config.verbose:
                    click.secho(
                        f"Found configuration files:\n    {', '.join(str(f[0]) for f in config_files)}",
                        fg="bright_black",
                    )
                config = load_config_from_path(*config_files)

            except (TypeError, ValueError) as e:
                raise click.ClickException(str(e)) from e

    if config is None:
        click.secho("No configuration found. 😥", fg="red", err=True)
        return 1

    return print_config(config, format, color)
