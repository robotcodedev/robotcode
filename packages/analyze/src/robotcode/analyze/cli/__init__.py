from typing import Union

import click

from ..__version__ import __version__


@click.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
    add_help_option=True,
)
@click.version_option(
    version=__version__,
    package_name="robotcode.analyze",
    prog_name="RobotCode Analyze",
)
@click.pass_context
def analyze(
    ctx: click.Context,
) -> Union[str, int, None]:
    """TODO: Analyzes a Robot Framework project.

    TODO: This is not implemented yet.
    """
    click.echo("Not implemented yet")
    return 0
