import io
import sys
from pathlib import Path
from typing import Optional, Tuple

import click
from robot.api import TestSuite, get_model
from robot.conf import RobotSettings
from robot.errors import DATA_ERROR, INFO_PRINTED, DataError, Information
from robot.output import LOGGER

from robotcode.plugin import (
    Application,
    pass_application,
)
from robotcode.plugin.click_helper.aliases import AliasedCommand
from robotcode.robot.utils import get_robot_version
from robotcode.runner.cli.robot import RobotFrameworkEx, handle_robot_options

from ..interpreter import Interpreter
from ..repl_listener import ReplListener

REPL_SUITE = """\
*** Settings ***
Library  robotcode.repl.Repl
*** Test Cases ***
RobotCode REPL
    repl
"""


def run_repl(
    app: Application,
    inspect: bool,
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    outputdir: Optional[str],
    files: Tuple[Path, ...],
) -> None:
    robot_options_and_args: Tuple[str, ...] = ()

    if files:
        files = tuple(f.absolute() for f in files)

    for var in variable:
        robot_options_and_args += ("--variable", var)
    for varfile in variablefile:
        robot_options_and_args += ("--variablefile", varfile)
    for pypath in pythonpath:
        robot_options_and_args += ("--pythonpath", pypath)
    if outputdir:
        robot_options_and_args += ("--outputdir", outputdir)

    root_folder, profile, cmd_options = handle_robot_options(app, (*robot_options_and_args, *(str(f) for f in files)))

    try:

        options, _ = RobotFrameworkEx(
            app,
            ["."],
            app.config.dry,
            root_folder,
        ).parse_arguments((*cmd_options, *robot_options_and_args))

        settings = RobotSettings(
            options,
            output=None,
            log=None,
            report=None,
            quiet=True,
            listener=[
                ReplListener(app, Interpreter(app, files=list(files), inspect=inspect)),
            ],
        )

        if app.show_diagnostics:
            LOGGER.register_console_logger(**settings.console_output_config)
        else:
            LOGGER.unregister_console_logger()

        LOGGER.unregister_console_logger()

        if get_robot_version() >= (5, 0):
            if settings.pythonpath:
                sys.path = settings.pythonpath + sys.path

        with io.StringIO(REPL_SUITE) as output:
            model = get_model(output)

            suite = TestSuite.from_model(model)
            suite.configure(**settings.suite_config)
            suite.run(settings)

    except Information as err:
        app.echo(str(err))
        app.exit(INFO_PRINTED)
    except DataError as err:
        app.error(str(err))
        app.exit(DATA_ERROR)


@click.command(
    cls=AliasedCommand,
    aliases=["shell"],
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
)
@click.option(
    "-v",
    "--variable",
    metavar="name:value",
    type=str,
    multiple=True,
    help="Set variables in the test data. see `robot --variable` option.",
)
@click.option(
    "-V",
    "--variablefile",
    metavar="path",
    type=str,
    multiple=True,
    help="Python or YAML file file to read variables from. see `robot --variablefile` option.",
)
@click.option(
    "-P",
    "--pythonpath",
    metavar="path",
    type=str,
    multiple=True,
    help="Additional locations (directories, ZIPs, JARs) where to search test libraries"
    " and other extensions when they are imported. see `robot --pythonpath` option.",
)
@click.option(
    "-d",
    "--outputdir",
    metavar="dir",
    type=str,
    help="Where to create output files. see `robot --outputdir` option.",
)
@click.option(
    "-i",
    "--inspect",
    is_flag=True,
    default=False,
    help="Activate inspection mode. This forces a prompt to appear after the REPL script is executed.",
)
@click.argument(
    "files",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    nargs=-1,
    required=False,
)
@pass_application
def repl(
    app: Application,
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    outputdir: Optional[str],
    inspect: bool,
    files: Tuple[Path, ...],
) -> None:
    """\
    Run Robot Framework interactively.
    """

    run_repl(app, inspect, variable, variablefile, pythonpath, outputdir, files)
