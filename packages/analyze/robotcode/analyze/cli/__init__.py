from typing import Tuple, Union

import click
from robot.run import USAGE
from robot.version import get_full_version

from ..__version__ import __version__


@click.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": ["-h", "--help"],
    },
    add_help_option=True,
)
@click.version_option(
    version=__version__,
    package_name="robotcode.analyze",
    prog_name="RobotCode Analyze",
    message=f"%(prog)s %(version)s\n{USAGE.splitlines()[0].split(' -- ')[0].strip()} {get_full_version()}",
)
@click.argument("robot_options_and_args", nargs=-1, type=click.Path())
@click.pass_context
def analyze(
    ctx: click.Context,
    robot_options_and_args: Tuple[str, ...],
) -> Union[str, int, None]:
    """Analyzes Robot Framework test data."""
    return 0
