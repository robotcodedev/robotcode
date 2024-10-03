from typing import Tuple, Union

import click

from robotcode.analyze.config import AnalyzeConfig
from robotcode.plugin import Application, pass_application
from robotcode.robot.config.loader import (
    load_robot_config_from_path,
)
from robotcode.robot.config.utils import get_config_files

from .__version__ import __version__


@click.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
)
@click.version_option(
    version=__version__,
    package_name="robotcode.analyze",
    prog_name="RobotCode Analyze",
)
@click.argument("paths", nargs=-1, type=click.Path(exists=True, dir_okay=True))
@pass_application
def analyze(app: Application, paths: Tuple[str]) -> Union[str, int, None]:
    """TODO: Analyzes a Robot Framework project."""

    config_files, root_folder, _ = get_config_files(
        paths,
        app.config.config_files,
        root_folder=app.config.root,
        no_vcs=app.config.no_vcs,
        verbose_callback=app.verbose,
    )

    try:
        robot_config = load_robot_config_from_path(
            *config_files, extra_tools={"robotcode-analyze": AnalyzeConfig}, verbose_callback=app.verbose
        )

        analyzer_config = robot_config.tool.get("robotcode-analyze", None) if robot_config.tool is not None else None
        if analyzer_config is None:
            analyzer_config = AnalyzeConfig()

        robot_profile = robot_config.combine_profiles(
            *(app.config.profiles or []), verbose_callback=app.verbose, error_callback=app.error
        ).evaluated_with_env()

        app.print_data(analyzer_config)
        app.print_data(robot_profile)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    return 0
