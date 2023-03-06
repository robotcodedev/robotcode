import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union, cast

import click
from robot.errors import DataError
from robot.run import USAGE, RobotFramework
from robot.version import get_full_version

from robotcode.config.model import RobotConfig

from ..__version__ import __version__

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class RobotFrameworkEx(RobotFramework):
    def __init__(self, arguments: List[str]) -> None:
        super().__init__()
        self.arguments = arguments

    def parse_arguments(self, cli_args: Any) -> Any:
        try:
            options, arguments = super().parse_arguments(cli_args)
        except DataError:
            options, arguments = super().parse_arguments((*cli_args, *self.arguments))

        if not arguments:
            arguments = self.arguments
        return options, arguments


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
    package_name="robotcode",
    prog_name="RobotCode Runner",
    message=f"%(prog)s %(version)s\n{USAGE.splitlines()[0].split(' -- ')[0].strip()} {get_full_version()}",
)
@click.argument("robot_options_and_args", nargs=-1, type=click.Path())
@click.pass_context
def run(
    ctx: click.Context,
    robot_options_and_args: Tuple[str, ...],
) -> Union[str, int, None]:
    """Runs robot with the given options and arguments.

    The options and arguments are passed to robot as is."""

    with open("robot.toml", "rb") as f:
        pyproject_toml = tomllib.load(f)

    model = RobotConfig(**pyproject_toml["robot"])

    options = []

    if model.output_dir:
        options += ["-d", model.output_dir]

    if model.python_path:
        for e in model.python_path:
            options += ["-P", e]

    if model.variables:
        for entry in model.variables:
            for k, v in entry.items():
                options += ["-v", f"{k}:{v}"]
    try:
        return cast(
            int,
            RobotFrameworkEx(model.paths or []).execute_cli(
                # (*options, *robot_options_and_args, *(model.paths or [])), exit=False
                (*options, *robot_options_and_args),
                exit=False,
            ),
        )
    except SystemExit as e:
        return e.code
