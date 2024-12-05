from pathlib import Path
from typing import Optional, Tuple

import click

from robotcode.plugin import Application, pass_application

from .__version__ import __version__
from .console_interpreter import ConsoleInterpreter
from .run import run_repl


@click.command(add_help_option=True)
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
@click.option(
    "-s",
    "--source",
    type=click.Path(path_type=Path),
    metavar="FILE",
    help="Specifies the path to a source file. This file must not exist and will neither be read nor written. "
    "It is used solely to set the current working directory for the REPL script "
    "and to assign a name to the internal suite.",
)
@click.version_option(version=__version__, prog_name="RobotCode REPL")
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
    source: Optional[Path],
    files: Tuple[Path, ...],
) -> None:
    """\
    Run Robot Framework interactively.
    """
    if files:
        files = tuple(f.absolute() for f in files)

    interpreter = ConsoleInterpreter(app, files=list(files), show_keywords=show_keywords, inspect=inspect)

    run_repl(
        interpreter=interpreter,
        app=app,
        variablefile=variable,
        variable=variablefile,
        pythonpath=pythonpath,
        outputdir=outputdir,
        output=output,
        report=report,
        log=log,
        xunit=xunit,
        source=source,
        files=files,
    )
