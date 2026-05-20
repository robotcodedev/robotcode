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
    "--no-history",
    is_flag=True,
    default=False,
    envvar="ROBOTCODE_REPL_NO_HISTORY",
    help="Don't load or save the persistent history file. In-session "
    "arrow-up recall still works, but nothing crosses session boundaries. "
    "Useful for AI-agent invocations or quick spike sessions you don't "
    "want polluting your shell's REPL history.",
)
@click.option(
    "--plain",
    is_flag=True,
    default=False,
    envvar="ROBOTCODE_REPL_PLAIN",
    help="Disable all prompt enhancements — completion, syntax highlighting, "
    "candidate popup, auto-suggest, history file. The prompt becomes a bare "
    "`input()` call. Recommended for AI-agent invocations, automation "
    "pipelines, and any context where ANSI escapes or completion popups "
    "would interfere with stdin/stdout capture.",
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
    help="Use the parent directory of FILE as the REPL's working directory. "
    "Relative paths inside `Import Resource`, `Import Library`, "
    "file-based variables, etc. resolve against that directory. "
    "The file itself is never read or written, so the path doesn't "
    "need to exist.",
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
    no_history: bool,
    plain: bool,
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

    interpreter = ConsoleInterpreter(
        app,
        files=list(files),
        show_keywords=show_keywords,
        inspect=inspect,
        no_history=no_history,
        plain=plain,
    )

    run_repl(
        interpreter=interpreter,
        app=app,
        variable=variable,
        variablefile=variablefile,
        pythonpath=pythonpath,
        outputdir=outputdir,
        output=output,
        report=report,
        log=log,
        xunit=xunit,
        source=source,
        files=files,
    )
