import sys
from typing import Any, List, Tuple, Union, cast

import click
from robot.errors import DataError, Information
from robot.run import USAGE, RobotFramework
from robot.version import get_full_version

from robotcode.core.dataclasses import from_dict
from robotcode.robot.config.model import MainProfile

from ..__version__ import __version__

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class RobotFrameworkEx(RobotFramework):
    def __init__(self, paths: List[str], dry: bool) -> None:
        super().__init__()
        self.paths = paths
        self.dry = dry

    def parse_arguments(self, cli_args: Any) -> Any:
        try:
            options, arguments = super().parse_arguments(cli_args)
        except DataError:
            options, arguments = super().parse_arguments((*cli_args, *self.paths))

        if not arguments:
            arguments = self.paths

        if self.dry:
            line_end = "\n"
            raise Information(
                "Dry run, not executing any commands. "
                f"Would execute robot with the following arguments:\n"
                f'{line_end.join((*(f"{k} = {repr(v)}" for k, v in options.items()) ,*arguments))}'
            )

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
    package_name="robotcode.runner",
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

    model = from_dict(pyproject_toml, MainProfile)

    options = []

    if model.output_dir:
        options += ["-d", model.output_dir]

    if model.python_path:
        for e in model.python_path:
            options += ["-P", e]

    if model.variables and isinstance(model.variables, dict):
        for k, v in model.variables.items():
            options += ["-v", f"{k}:{v}"]

    try:
        return cast(
            int,
            RobotFrameworkEx(
                [] if model.paths is None else model.paths if isinstance(model.paths, list) else [model.paths],
                ctx.obj["dry"],
            ).execute_cli(
                (*options, *robot_options_and_args),
                exit=False,
            ),
        )
    except SystemExit as e:
        return cast(int, e.code)
