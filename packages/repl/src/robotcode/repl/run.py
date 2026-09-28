import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from robot.api import TestSuite, get_model
from robot.conf import RobotSettings
from robot.errors import DATA_ERROR, INFO_PRINTED, DataError, Information
from robot.output import LOGGER
from robot.reporting import ResultWriter

from robotcode.core.utils.path import normalized_path
from robotcode.plugin import (
    Application,
)
from robotcode.runner.cli.robot import RobotFrameworkEx, handle_robot_options

from .base_interpreter import BaseInterpreter

REPL_SUITE = """\
*** Settings ***
Library  robotcode.repl.Repl
*** Test Cases ***
RobotCode REPL
    repl
"""

# Options from robot.toml, `args`, argument files or ROBOT_OPTIONS that are meant for real
# suites. Applied to REPL_SUITE they deselect or skip its only test, so the REPL never
# starts, or turn the session into a dry run in which nothing typed is executed. The
# other skip options are dropped along with them.
_IGNORED_ROBOT_OPTIONS = (
    "include",
    "exclude",
    "suite",
    "test",
    "task",
    "rerunfailed",
    "rerunfailedsuites",
    "dryrun",
    "settag",
    "skip",
    "skiponfailure",
    "skipteardownonexit",
)


@dataclass
class ReplResult:
    """How a REPL session ended."""

    # Robot Framework's return code for the session test: 1 when it failed, 0 when it
    # passed or when `statusrc` is switched off.
    return_code: int
    # The code given to `.exit`/`.quit`, None without one.
    exit_code: Optional[int]


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
    statusrc: Optional[bool] = None,
) -> ReplResult:
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
    # Parsed after the configured options, so Robot's "last one wins" lets it override them.
    if statusrc is not None:
        robot_options_and_args += ("--statusrc" if statusrc else "--nostatusrc",)

    root_folder, _profile, cmd_options = handle_robot_options(app, (*robot_options_and_args, *(str(f) for f in files)))

    # Resolved before `app.chdir`, so a relative `--source` is relative to where the
    # REPL was started (like FILES), not to the project root.
    source = normalized_path(source if source is not None else Path.cwd() / "__repl_internal__.robot")

    with app.chdir(root_folder) as orig_folder:
        try:
            options, _ = RobotFrameworkEx(
                app,
                ["."],
                app.config.dry,
                root_folder=root_folder,
                orig_folder=orig_folder,
            ).parse_arguments((*cmd_options, *robot_options_and_args))

            # Every key is dropped, but only options that are actually set (not e.g. `--nodryrun`) are reported.
            ignored = [key for key in _IGNORED_ROBOT_OPTIONS if options.pop(key, None)]
            if ignored:
                app.verbose(f"Ignoring robot options in the REPL: {', '.join(ignored)}")

            interpreter.source = source

            settings = RobotSettings(
                options,
                console="NONE",
                output=output,
                log=log,
                report=report,
                xunit=xunit,
                quiet=True,
            )

            if app is not None and app.show_diagnostics:
                LOGGER.register_console_logger(**settings.console_output_config)
            else:
                LOGGER.unregister_console_logger()

            if settings.pythonpath:
                sys.path = settings.pythonpath + sys.path

            with io.StringIO(REPL_SUITE) as suite_io:
                model = get_model(suite_io, curdir=str(source.parent).replace("\\", "\\\\"))
                # RF < 6.1 expects a `str` suite source; RF 6.1+ converts it to a `Path` itself.
                model.source = str(source)

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

    # The prompt loop runs inside `suite.run`, so a code given to `.exit` is known by now.
    return ReplResult(result.return_code, interpreter.exit_code)
