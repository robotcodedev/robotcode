import io
import sys
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Tuple

from robot.api import TestSuite, get_model
from robot.conf import RobotSettings
from robot.errors import DATA_ERROR, INFO_PRINTED, DataError, Information
from robot.output import LOGGER
from robot.reporting import ResultWriter

from robotcode.core.utils.path import normalized_path
from robotcode.plugin import (
    Application,
)
from robotcode.robot.utils import get_robot_version
from robotcode.runner.cli.robot import RobotFrameworkEx, handle_robot_options

from .base_interpreter import BaseInterpreter

REPL_SUITE = """\
*** Settings ***
Library  robotcode.repl.Repl
*** Test Cases ***
RobotCode REPL
    repl
"""


class ReplListener:
    ROBOT_LISTENER_API_VERSION = 2
    instance: ClassVar["ReplListener"]

    def __init__(self, app: Application, interpreter: BaseInterpreter) -> None:
        ReplListener.instance = self
        self.app = app
        self.interpreter = interpreter

    def start_keyword(
        self,
        name: str,
        attributes: Dict[str, Any],
    ) -> None:
        if name != "robotcode.repl.Repl.Repl":
            return

        self.interpreter.run()


def run_repl(
    interpreter: BaseInterpreter,
    app: Application,
    variable: Tuple[str, ...] = (),
    variablefile: Tuple[str, ...] = (),
    pythonpath: Tuple[str, ...] = (),
    outputdir: Optional[str] = None,
    output: Optional[str] = None,
    report: Optional[str] = None,
    log: Optional[str] = None,
    xunit: Optional[str] = None,
    source: Optional[Path] = None,
    files: Tuple[Path, ...] = (),
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

    with app.chdir(root_folder) as orig_folder:
        try:
            curdir = normalized_path(source).parent if source is not None else Path.cwd()

            options, _ = RobotFrameworkEx(
                app,
                ["."],
                app.config.dry,
                root_folder=root_folder,
                orig_folder=orig_folder,
            ).parse_arguments((*cmd_options, *robot_options_and_args))

            interpreter.source = source

            settings = RobotSettings(
                options,
                outputdir=str(curdir),
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
                model = get_model(suite_io, curdir=str(curdir).replace("\\", "\\\\"))

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
