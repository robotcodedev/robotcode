import os
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union, cast

import click
from robot.errors import DataError, Information
from robot.run import USAGE, RobotFramework
from robot.version import get_full_version

from robotcode.plugin import Application, pass_application
from robotcode.robot.config.loader import find_project_root, get_config_files_from_folder, load_config_from_path
from robotcode.robot.config.model import RobotBaseProfile

from ..__version__ import __version__


class RobotFrameworkEx(RobotFramework):
    def __init__(self, paths: List[str], dry: bool, root_folder: Optional[Path]) -> None:
        super().__init__()
        self.paths = paths
        self.dry = dry
        self.root_folder = root_folder

    def parse_arguments(self, cli_args: Any) -> Any:
        try:
            options, arguments = super().parse_arguments(cli_args)
        except DataError:
            options, arguments = super().parse_arguments((*cli_args, *self.paths))

        if not arguments:
            arguments = self.paths

        if self.root_folder is not None:
            for i, arg in enumerate(arguments.copy()):
                if Path(arg).is_absolute():
                    continue

                arguments[i] = str(Path(arg).absolute().relative_to(self.root_folder))

        if self.dry:
            line_end = "\n"
            raise Information(
                "Dry run, not executing any commands. "
                f"Would execute robot with the following arguments:\n"
                f'{line_end.join((*(f"{k} = {repr(v)}" for k, v in options.items()) ,*arguments))}'
            )

        return options, arguments

    def main(self, arguments: Any, **options: Any) -> Any:
        if self.root_folder is not None:
            os.chdir(self.root_folder)

        super().main(arguments, **options)


@click.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
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
@pass_application
def robot(
    app: Application,
    robot_options_and_args: Tuple[str, ...],
) -> Union[str, int, None]:
    """Runs "robot" with the selected configuration, profiles, options and arguments.

    The options and arguments are passed to "robot" as is.

    Use "-- --help" to see the robot help.
    """

    robot_arguments = None
    try:
        _, robot_arguments = RobotFramework().parse_arguments(robot_options_and_args)
    except (DataError, Information):
        pass

    root_folder, discovered_by = find_project_root(*(robot_arguments or []))
    app.verbose(lambda: f"Found project root at:\n    {root_folder} ({discovered_by.value})")

    profile: Optional[RobotBaseProfile] = None

    if root_folder is not None:
        config_files = get_config_files_from_folder(root_folder)
        if config_files:
            app.verbose(lambda: f"Found configuration files:\n    {', '.join(str(f[0]) for f in config_files)}")
            try:
                profile = load_config_from_path(*config_files).combine_profiles(
                    *app.config.profiles if app.config.profiles else [],
                    verbose_callback=app.verbose if app.config.verbose else None,
                )
            except (TypeError, ValueError) as e:
                raise click.ClickException(str(e)) from e

        else:
            app.verbose("No configuration files found.")

    if profile is None:
        profile = RobotBaseProfile()

    options = profile.build_command_line()

    if profile.env:
        for k, v in profile.env.items():
            os.environ[k] = v
            app.verbose(lambda: f"Set environment variable {k} to {v}")
    try:
        app.verbose(
            lambda: " Executing robot with the following options:\n    "
            + " ".join(f'"{o}"' for o in (options + list(robot_options_and_args)))
        )
        return cast(
            int,
            RobotFrameworkEx(
                [] if profile.paths is None else profile.paths if isinstance(profile.paths, list) else [profile.paths],
                app.config.dry,
                root_folder,
            ).execute_cli(
                (*options, *robot_options_and_args),
                exit=False,
            ),
        )
    except SystemExit as e:
        return cast(int, e.code)
