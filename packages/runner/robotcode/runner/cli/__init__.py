import functools
from typing import Any, List, Optional, Tuple, Union, cast

import click
from robot.errors import DataError, Information
from robot.run import USAGE, RobotFramework
from robot.version import get_full_version

from robotcode.plugin import CommonConfig, pass_common_config
from robotcode.robot.config.loader import find_project_root, get_config_files_from_folder, load_config_from_path
from robotcode.robot.config.model import BaseProfile

from ..__version__ import __version__


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
    short_help='Runs "robot" with the selected configuration, profiles, options and arguments.',
)
@click.version_option(
    version=__version__,
    package_name="robotcode.runner",
    prog_name="RobotCode Runner",
    message=f"%(prog)s %(version)s\n{USAGE.splitlines()[0].split(' -- ')[0].strip()} {get_full_version()}",
)
@click.argument("robot_options_and_args", nargs=-1, type=click.Path())
@click.pass_context
@pass_common_config
def run(
    common_config: CommonConfig,
    ctx: click.Context,
    robot_options_and_args: Tuple[str, ...],
) -> Union[str, int, None]:
    """Runs "robot" with the selected configuration, profiles, options and arguments.

    The options and arguments are passed to robot as is.

    Use "-- --help" to see the robot help.
    """

    arguments = None
    try:
        _, arguments = RobotFramework().parse_arguments(robot_options_and_args)
    except (DataError, Information):
        pass

    root_folder, discovered_by = find_project_root(*(arguments or []))
    if common_config.verbose:
        click.secho(f"Found project root at:\n    {root_folder} ({discovered_by})", fg="bright_black")

    profile: Optional[BaseProfile] = None

    if root_folder is not None:
        config_files = get_config_files_from_folder(root_folder)
        if config_files:
            if common_config.verbose:
                click.secho(
                    f"Found configuration files:\n    {', '.join(str(f[0]) for f in config_files)}", fg="bright_black"
                )
            try:
                profile = load_config_from_path(*config_files).get_profile(
                    *common_config.profiles if common_config.profiles else [],
                    verbose_callback=functools.partial(click.secho, fg="bright_black")
                    if common_config.verbose
                    else None,
                )
            except TypeError as e:
                raise click.ClickException(str(e)) from e

        else:
            if common_config.verbose:
                click.secho("No configuration files found.", fg="bright_black")

    if profile is None:
        profile = BaseProfile()

    options = []

    if profile.output_dir:
        options += ["-d", profile.output_dir]

    if profile.python_path:
        for v in profile.python_path:
            options += ["-P", v]

    if profile.variables and isinstance(profile.variables, dict):
        for k, v in profile.variables.items():
            options += ["-v", f"{k}:{v}"]

    try:
        return cast(
            int,
            RobotFrameworkEx(
                profile.paths or [],
                common_config.dry,
            ).execute_cli(
                (*options, *robot_options_and_args),
                exit=False,
            ),
        )
    except SystemExit as e:
        return cast(int, e.code)
