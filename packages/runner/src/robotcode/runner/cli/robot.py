import os
import sys
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple, Union, cast

import click
from robot.errors import DataError, Information
from robot.run import USAGE, RobotFramework
from robot.version import get_full_version
from robotcode.plugin import Application, pass_application
from robotcode.plugin.click_helper.aliases import AliasedCommand
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.config.utils import get_config_files

from ..__version__ import __version__


class RobotFrameworkEx(RobotFramework):
    def __init__(self, app: Application, paths: List[str], dry: bool, root_folder: Optional[Path]) -> None:
        super().__init__()
        self.app = app
        self.paths = paths
        self.dry = dry
        self.root_folder = root_folder
        self._orig_cwd = Path.cwd()

    def parse_arguments(self, cli_args: Any) -> Any:
        if self.root_folder is not None and Path.cwd() != self.root_folder:
            self.app.verbose(f"Changing working directory from {self._orig_cwd} to {self.root_folder}")
            os.chdir(self.root_folder)

        try:
            options, arguments = super().parse_arguments(cli_args)
            if self.root_folder is not None:
                for i, arg in enumerate(arguments.copy()):
                    if Path(arg).is_absolute():
                        continue

                    arguments[i] = str((self._orig_cwd / Path(arg)).absolute().relative_to(self.root_folder))

        except DataError:
            options, arguments = super().parse_arguments((*cli_args, *self.paths))

        if not arguments:
            arguments = self.paths

        if self.dry:
            line_end = "\n"
            raise Information(
                "Dry run, not executing any commands. "
                f"Would execute robot with the following options and arguments:\n"
                f'{line_end.join((*(f"{k} = {v!r}" for k, v in options.items()) ,*arguments))}'
            )

        return options, arguments


# mypy: disable-error-code="arg-type"

ROBOT_OPTIONS: Set[click.Command] = {
    click.option("--by-longname", type=str, multiple=True, help="Select tests/tasks or suites by longname."),
    click.option(
        "--exclude-by-longname",
        type=str,
        multiple=True,
        help="Excludes tests/tasks or suites by longname.",
    ),
    click.version_option(
        version=__version__,
        package_name="robotcode.runner",
        prog_name="RobotCode Runner",
        message=f"%(prog)s %(version)s\n{USAGE.splitlines()[0].split(' -- ')[0].strip()} {get_full_version()}",
    ),
    click.argument("robot_options_and_args", nargs=-1, type=click.Path()),
}


def handle_robot_options(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> Tuple[Optional[Path], RobotBaseProfile, List[str]]:
    robot_arguments: Optional[List[Union[str, Path]]] = None
    old_sys_path = sys.path.copy()
    try:
        _, robot_arguments = RobotFramework().parse_arguments(robot_options_and_args)
    except (DataError, Information):
        pass
    finally:
        sys.path = old_sys_path

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

    cmd_options = profile.build_command_line()

    if by_longname:
        sep = ";" if any(True for l in by_longname if ":" in l) else ":"
        cmd_options += ("--prerunmodifier", f"robotcode.modifiers.ByLongName{sep}{sep.join(by_longname)}")

    if exclude_by_longname:
        sep = ";" if any(True for l in exclude_by_longname if ":" in l) else ":"
        cmd_options += (
            "--prerunmodifier",
            f"robotcode.modifiers.ExcludedByLongName{sep}{sep.join(exclude_by_longname)}",
        )

    if profile.env:
        for k, v in profile.env.items():
            os.environ[k] = v
            app.verbose(lambda: f"Set environment variable {k} to {v}")

    app.verbose(
        lambda: "Executing robot with following options:\n    "
        + " ".join(f'"{o}"' for o in (cmd_options + list(robot_options_and_args)))
    )

    return root_folder, profile, cmd_options


@click.command(
    cls=AliasedCommand,
    aliases=["run"],
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
    add_help_option=True,
    epilog='Use "-- --help" to see `robot` help.',
)
@add_options(*ROBOT_OPTIONS)
@pass_application
def robot(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """Runs `robot` with the selected configuration, profiles, options and arguments.

    The options and arguments are passed to `robot` as is.

    Examples:

    \b
    ```
    robotcode robot
    robotcode robot tests
    robotcode robot -i regression -e wip tests
    robotcode --profile ci robot -i regression -e wip tests
    ```
    """

    root_folder, profile, cmd_options = handle_robot_options(
        app, by_longname, exclude_by_longname, robot_options_and_args
    )

    app.exit(
        cast(
            int,
            RobotFrameworkEx(
                app,
                [*(app.config.default_paths if app.config.default_paths else ())]
                if profile.paths is None
                else profile.paths
                if isinstance(profile.paths, list)
                else [profile.paths],
                app.config.dry,
                root_folder,
            ).execute_cli(
                (*cmd_options, *robot_options_and_args),
                exit=False,
            ),
        )
    )
