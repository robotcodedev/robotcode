# ruff: noqa: RUF009
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import click
from robotcode.plugin import Application, pass_application
from robotcode.robot.config.loader import load_config_from_path
from robotcode.robot.config.model import BaseOptions, field
from robotcode.robot.config.utils import get_config_files

from .__version__ import __version__


@dataclass
class Dummy:
    some_field: Optional[str] = field(default="some value", description="Some field")


@dataclass
class AnalyzerConfig(BaseOptions):
    select: Optional[List[Union[str, Dummy]]] = field(description="Selects which rules are run.")
    extra_select: Optional[List[Union[str, Dummy]]] = field(description="Selects which rules are run.")
    ignore: Optional[List[str]] = field(description="Ignores which rules are run.")
    extra_ignore: Optional[List[str]] = field(description="Ignores which rules are run.")


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
        robot_profile = load_config_from_path(
            AnalyzerConfig, *config_files, tool_name="robotcode-analyze", robot_toml_tool_name="robotcode-analyze"
        ).evaluated()
    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    app.print_data(robot_profile)
    return 0
