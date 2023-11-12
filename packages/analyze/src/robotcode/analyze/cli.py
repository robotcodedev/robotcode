from typing import Tuple, Union

import click
from robotcode.analyze.config import AnalyzerConfig
from robotcode.plugin import Application, pass_application
from robotcode.robot.config.loader import load_config_from_path, load_robot_config_from_path
from robotcode.robot.config.utils import get_config_files

from .__version__ import __version__


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
@click.argument("paths", nargs=-1, type=click.Path(exists=True, dir_okay=True))
@pass_application
def analyze(
    app: Application,
    paths: Tuple[str],
) -> Union[str, int, None]:
    """TODO: Analyzes a Robot Framework project."""

    config_files, root_folder, _ = get_config_files(paths, app.config.config_files, verbose_callback=app.verbose)

    try:
        analizer_config = load_config_from_path(
            AnalyzerConfig, *config_files, tool_name="robotcode-analyze", robot_toml_tool_name="robotcode-analyze"
        ).evaluated()

        robot_config = (
            load_robot_config_from_path(*config_files).combine_profiles(*(app.config.profiles or [])).evaluated()
        )

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    app.print_data(analizer_config)
    app.print_data(robot_config)

    return 0
