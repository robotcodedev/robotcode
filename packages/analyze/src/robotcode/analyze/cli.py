import click

from robotcode.plugin import Application, pass_application

from .__version__ import __version__
from .code.cli import code


@click.group(
    add_help_option=True,
    invoke_without_command=False,
)
@click.version_option(
    version=__version__,
    package_name="robotcode.analyze",
    prog_name="RobotCode Analyze",
)
@pass_application
def analyze(app: Application) -> None:
    """\
    The analyze command provides various subcommands for analyzing Robot Framework code.
    These subcommands support specialized tasks, such as code analysis, style checking or dependency graphs.
    """


analyze.add_command(code)
