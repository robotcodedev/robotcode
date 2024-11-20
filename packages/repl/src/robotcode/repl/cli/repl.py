import io
import sys
from pathlib import Path
from typing import Optional, Tuple

import click
from robot.api import TestSuite, get_model
from robot.conf import RobotSettings
from robot.errors import DATA_ERROR, INFO_PRINTED, DataError, Information
from robot.output import LOGGER
from robot.reporting import ResultWriter

from robotcode.plugin import (
    Application,
    pass_application,
)
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
    inspect: bool = False,
    variable: Tuple[str, ...] = (),
    variablefile: Tuple[str, ...] = (),
    pythonpath: Tuple[str, ...] = (),
    outputdir: Optional[str] = None,
    output: Optional[str] = None,
    report: Optional[str] = None,
    log: Optional[str] = None,
    xunit: Optional[str] = None,
    files: Tuple[Path, ...] = (),
    show_keywords: bool = False,
    interpreter: Optional[Interpreter] = None,
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

    root_folder, _profile, cmd_options = handle_robot_options(app, (*robot_options_and_args, *(str(f) for f in files)))

    try:

        options, _ = RobotFrameworkEx(
            app,
            ["."],
            app.config.dry,
            root_folder,
        ).parse_arguments((*cmd_options, *robot_options_and_args))

        if interpreter is None:
            interpreter = Interpreter(app, files=list(files), show_keywords=show_keywords, inspect=inspect)

        settings = RobotSettings(
            options,
            console="NONE",
            output=output,
            log=log,
            report=report,
            xunit=xunit,
            quiet=True,
            listener=[
                ReplListener(app, interpreter),
            ],
        )

        if app is not None and app.show_diagnostics:
            LOGGER.register_console_logger(**settings.console_output_config)
        else:
            LOGGER.unregister_console_logger()

        if get_robot_version() >= (5, 0):
            if settings.pythonpath:
                sys.path = settings.pythonpath + sys.path

        with io.StringIO(REPL_SUITE) as suite_io:
            model = get_model(suite_io)

            suite = TestSuite.from_model(model)
            suite.configure(**settings.suite_config)
            result = suite.run(settings)

            if settings.log or settings.report or settings.xunit:
                writer = ResultWriter(settings.output if settings.log else result)
                writer.write_results(settings.get_rebot_settings())

    except Information as err:
        app.echo(str(err))
        app.exit(INFO_PRINTED)
    except DataError as err:
        app.error(str(err))
        app.exit(DATA_ERROR)


@click.command(
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
    metavar="PATH",
    type=str,
    multiple=True,
    help="Python or YAML file file to read variables from. see `robot --variablefile` option.",
)
@click.option(
    "-P",
    "--pythonpath",
    metavar="PATH",
    type=str,
    multiple=True,
    help="Additional locations where to search test libraries"
    " and other extensions when they are imported. see `robot --pythonpath` option.",
)
@click.option(
    "-k",
    "--show-keywords",
    is_flag=True,
    default=False,
    help="Executed keywords will be shown in the output.",
)
@click.option(
    "-i",
    "--inspect",
    is_flag=True,
    default=False,
    help="Activate inspection mode. This forces a prompt to appear after the REPL script is executed.",
)
@click.option(
    "-d",
    "--outputdir",
    metavar="DIR",
    type=str,
    help="Where to create output files. see `robot --outputdir` option.",
)
@click.option(
    "-o",
    "--output",
    metavar="FILE",
    type=str,
    help="XML output file. see `robot --output` option.",
)
@click.option(
    "-r",
    "--report",
    metavar="FILE",
    type=str,
    help="HTML output file. see `robot --report` option.",
)
@click.option(
    "-l",
    "--log",
    metavar="FILE",
    type=str,
    help="HTML log file. see `robot --log` option.",
)
@click.option(
    "-x",
    "--xunit",
    metavar="FILE",
    type=str,
    help="xUnit output file. see `robot --xunit` option.",
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
    show_keywords: bool,
    inspect: bool,
    outputdir: Optional[str],
    output: Optional[str],
    report: Optional[str],
    log: Optional[str],
    xunit: Optional[str],
    files: Tuple[Path, ...],
) -> None:
    """\
    Run Robot Framework interactively.
    """

    run_repl(
        app=app,
        inspect=inspect,
        variablefile=variable,
        variable=variablefile,
        pythonpath=pythonpath,
        outputdir=outputdir,
        output=output,
        report=report,
        log=log,
        xunit=xunit,
        files=files,
        show_keywords=show_keywords,
    )
