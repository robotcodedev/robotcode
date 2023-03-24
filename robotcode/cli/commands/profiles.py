from pathlib import Path
from typing import List, Union

import click

from robotcode.core.dataclasses import as_dict
from robotcode.plugin import ClickCommonConfig, pass_common_config
from robotcode.robot.config.loader import (
    load_config_from_path,
)

from ._common import get_config_files, print_dict


@click.group(
    invoke_without_command=False,
)
@pass_common_config
def profiles(
    common_config: ClickCommonConfig,
) -> Union[str, int, None]:
    """Commands to give informations about Robot Framework profiles."""

    return 0


@profiles.command
@click.option(
    "-p",
    "--profile",
    "profiles",
    type=str,
    multiple=True,
    show_envvar=True,
    help="""\
        The Execution Profile to use. Can be specified multiple times.
        If not specified, the default profile is used.
        """,
)
@click.option(
    "-f", "--format", "format", type=click.Choice(["json", "toml"]), default="toml", help="Set the output format."
)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_common_config
def show(
    common_config: ClickCommonConfig,
    format: str,
    profiles: List[str],
    paths: List[Path],
) -> Union[str, int, None]:
    """Shows the given Robot Framework profile.

    If no profile is given, the default profile is shown, if it is defined."""

    config_files = get_config_files(common_config, paths)
    if not config_files:
        raise click.ClickException("Cannot find any configuration file. 😥")

    try:
        profile = load_config_from_path(*config_files).get_profile(*(*(common_config.profiles or []), *profiles))

        print_dict(as_dict(profile, remove_defaults=True), format, common_config.colored_output)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    return 0


@profiles.command
@click.option(
    "-f",
    "--format",
    "format",
    type=click.Choice(["flat", "json", "toml"]),
    default="flat",
    help="Set the output format.",
)
@click.argument("paths", type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@pass_common_config
def list(
    common_config: ClickCommonConfig,
    format: str,
    paths: List[Path],
) -> Union[str, int, None]:
    """List the defined profiles in the given Robot Framework configuration."""

    config_files = get_config_files(common_config, paths)
    if not config_files:
        raise click.ClickException("Cannot find any configuration file. 😥")

    try:
        config = load_config_from_path(*config_files)

        result = {"profiles": {k: {"description": v.description or ""} for k, v in (config.profiles or {}).items()}}

        if format == "flat":
            for profile in result["profiles"]:
                click.secho(profile)
        else:
            print_dict(result, format, common_config.colored_output)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    return 0
