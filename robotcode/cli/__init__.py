from pathlib import Path
from typing import List, Optional

import click

from robotcode.plugin import ClickCommonConfig, ColoredOutput, pass_common_config
from robotcode.plugin.manager import PluginManager

from .__version__ import __version__
from .commands import config, profiles


@click.group(
    context_settings={"auto_envvar_prefix": "ROBOTCODE"},
    invoke_without_command=False,
)
@click.version_option(version=__version__, prog_name="robotcode")
@click.option(
    "-c",
    "--config",
    "config_file",
    type=click.Path(exists=True, path_type=Path),
    show_envvar=True,
    help="Config file to use.",
)
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
@click.option("-d", "--dry", is_flag=True, show_envvar=True, help="Dry run, do not execute any commands.")
@click.option(
    "--color / --no-color",
    "color",
    default=None,
    help="Whether or not to display colored output (default is auto-detection).",
    show_envvar=True,
)
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode.")
@click.pass_context
@pass_common_config
def robotcode(
    common_config: ClickCommonConfig,
    ctx: click.Context,
    config_file: Optional[Path],
    profiles: Optional[List[str]],
    dry: bool,
    verbose: bool,
    color: Optional[bool],
) -> None:
    """\b
 _____       _           _    _____          _
|  __ \\     | |         | |  / ____|        | |
| |__) |___ | |__   ___ | |_| |     ___   __| | ___
|  _  // _ \\| '_ \\ / _ \\| __| |    / _ \\ / _  |/ _ \\
| | \\ \\ (_) | |_) | (_) | |_| |___| (_) | (_| |  __/
|_|  \\_\\___/|_.__/ \\___/ \\__|\\_____\\___/ \\__,_|\\___|

"""
    common_config.config_file = config_file
    common_config.profiles = profiles
    common_config.dry = dry
    common_config.verbose = verbose
    if color is None:
        common_config.colored_output = ColoredOutput.AUTO
    elif color:
        common_config.colored_output = ColoredOutput.YES
    else:
        common_config.colored_output = ColoredOutput.NO


robotcode.add_command(config)
robotcode.add_command(profiles)

for p in PluginManager().cli_commands:
    for c in p:
        robotcode.add_command(c)


@robotcode.command()
@click.pass_context
def debug(ctx: click.Context) -> None:
    """Debug a Robot Framework run."""
    click.echo("TODO")


@robotcode.command()
@click.pass_context
def clean(ctx: click.Context) -> None:
    """Cleans a Robot Framework project."""
    click.echo("TODO")


@robotcode.command()
@click.pass_context
def new(ctx: click.Context) -> None:
    """Create a new Robot Framework project."""
    click.echo("TODO")
