import os
from pathlib import Path
from typing import Any, Optional, Tuple, cast

import click
from robot.errors import DataError, Information
from robot.rebot import USAGE, Rebot
from robot.version import get_full_version

from robotcode.plugin import Application, pass_application
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.model import RebotProfile
from robotcode.robot.config.utils import get_config_files
from robotcode.robot.utils import get_robot_version

from ..__version__ import __version__


class RebotEx(Rebot):
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
                f'{line_end.join((*(f"{k} = {v!r}" for k, v in options.items()), *arguments))}'
            )

        return options, arguments

    def main(self, datasources: Any, **options: Any) -> Any:
        if self.root_folder is not None:
            os.chdir(self.root_folder)

        return super().main(datasources, **options)


@click.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `rebot` help.",
)
@click.version_option(
    version=__version__,
    package_name="robotcode.runner.rebot",
    prog_name="RobotCode rebot",
    message=f"%(prog)s %(version)s\n{USAGE.splitlines()[0].split(' -- ')[0].strip()} {get_full_version()}",
)
@click.argument("robot_options_and_args", nargs=-1, type=click.Path())
@pass_application
def rebot(app: Application, robot_options_and_args: Tuple[str, ...]) -> None:
    """Runs `rebot` with the selected configuration, profiles, options and arguments.

    The options and arguments are passed to `rebot` as is.
    """

    robot_arguments = None
    try:
        _, robot_arguments = Rebot().parse_arguments(robot_options_and_args)
    except (DataError, Information):
        pass

    config_files, root_folder, _ = get_config_files(
        robot_arguments,
        app.config.config_files,
        root_folder=app.config.root,
        no_vcs=app.config.no_vcs,
        verbose_callback=app.verbose,
    )

    try:
        profile = (
            load_robot_config_from_path(*config_files, verbose_callback=app.verbose)
            .combine_profiles(*(app.config.profiles or []), verbose_callback=app.verbose, error_callback=app.error)
            .evaluated_with_env(verbose_callback=app.verbose, error_callback=app.error)
        )

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    rebot_options = profile.rebot
    if rebot_options is None:
        rebot_options = RebotProfile()

    rebot_options.add_options(profile)

    try:
        options = rebot_options.build_command_line()
    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    app.verbose(
        lambda: "Executing rebot with the following options:\n    "
        + " ".join(f'"{o}"' for o in (options + list(robot_options_and_args)))
    )

    console_links_args = []
    if get_robot_version() >= (7, 1) and os.getenv("ROBOTCODE_DISABLE_ANSI_LINKS", "").lower() in [
        "on",
        "1",
        "yes",
        "true",
    ]:
        console_links_args = ["--consolelinks", "off"]

    app.exit(
        cast(
            int,
            RebotEx(app.config.dry, root_folder).execute_cli(
                (*options, *console_links_args, *robot_options_and_args), exit=False
            ),
        )
    )
