import os
from pathlib import Path
from typing import Any, Optional, Tuple, cast

import click
from robot.errors import DataError, Information
from robot.libdoc import USAGE, LibDoc
from robot.version import get_full_version
from robotcode.plugin import Application, pass_application
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.model import LibDocProfile
from robotcode.robot.config.utils import get_config_files

from ..__version__ import __version__


class LibDocEx(LibDoc):
    def __init__(self, dry: bool, root_folder: Optional[Path]) -> None:
        super().__init__()
        self.dry = dry
        self.root_folder = root_folder

    def parse_arguments(self, cli_args: Any) -> Any:
        options, arguments = super().parse_arguments(cli_args)

        if self.dry:
            line_end = "\n"
            raise Information(
                "Dry run, not executing any commands. "
                f"Would execute libdoc with the following options and arguments:\n"
                f'{line_end.join((*(f"{k} = {v!r}" for k, v in options.items()) ,*arguments))}'
            )

        return options, arguments

    def main(self, arguments: Any, **options: Any) -> Any:
        if self.root_folder is not None:
            os.chdir(self.root_folder)

        return super().main(arguments, **options)


@click.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
    add_help_option=True,
    epilog='Use "-- --help" to see the `libdoc` help.',
)
@click.version_option(
    version=__version__,
    package_name="robotcode.runner.libdoc",
    prog_name="RobotCode libdoc",
    message=f"%(prog)s %(version)s\n{USAGE.splitlines()[0].split(' -- ')[0].strip()} {get_full_version()}",
)
@click.argument("robot_options_and_args", nargs=-1, type=click.Path())
@pass_application
def libdoc(
    app: Application,
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """Runs `libdoc` with the selected configuration, profiles, options and arguments.

    The options and arguments are passed to `libdoc` as is.
    """

    robot_arguments = None
    try:
        _, robot_arguments = LibDoc().parse_arguments(robot_options_and_args)
    except (DataError, Information):
        pass

    config_files, root_folder, _ = get_config_files(
        robot_arguments, app.config.config_files, verbose_callback=app.verbose
    )
    try:
        profile = (
            load_robot_config_from_path(*config_files)
            .combine_profiles(*(app.config.profiles or []), verbose_callback=app.verbose)
            .evaluated()
        )
    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    libdoc_options = profile.libdoc
    if libdoc_options is None:
        libdoc_options = LibDocProfile()

    libdoc_options.add_options(profile)

    options = libdoc_options.build_command_line()

    if profile.env:
        for k, v in profile.env.items():
            os.environ[k] = v
            app.verbose(lambda: f"Set environment variable {k} to {v}")

    app.verbose(
        lambda: "Executing libdoc robot with the following options:\n    "
        + " ".join(f'"{o}"' for o in (options + list(robot_options_and_args)))
    )

    app.exit(
        cast(
            int,
            LibDocEx(app.config.dry, root_folder).execute_cli((*options, *robot_options_and_args), exit=False),
        )
    )
