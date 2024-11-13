from pathlib import Path
from textwrap import indent
from typing import List, Optional, Set, Tuple

import click

from robotcode.analyze.config import AnalyzeConfig
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.path import try_get_relative_path
from robotcode.core.workspace import WorkspaceFolder
from robotcode.plugin import Application, pass_application
from robotcode.robot.config.loader import (
    load_robot_config_from_path,
)
from robotcode.robot.config.utils import get_config_files

from .__version__ import __version__
from .code_analyzer import CodeAnalyzer, DocumentDiagnosticReport, FolderDiagnosticReport


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


SEVERITY_COLORS = {
    DiagnosticSeverity.ERROR: "red",
    DiagnosticSeverity.WARNING: "yellow",
    DiagnosticSeverity.INFORMATION: "blue",
    DiagnosticSeverity.HINT: "cyan",
}


class Statistic:
    def __init__(self) -> None:
        self.folders: Set[WorkspaceFolder] = set()
        self.files: Set[TextDocument] = set()
        self.errors = 0
        self.warnings = 0
        self.infos = 0
        self.hints = 0

    def __str__(self) -> str:
        return (
            f"Files: {len(self.files)}, Errors: {self.errors}, Warnings: {self.warnings}, "
            f"Infos: {self.infos}, Hints: {self.hints}"
        )


@analyze.command(
    add_help_option=True,
)
@click.version_option(
    version=__version__,
    package_name="robotcode.analyze",
    prog_name="RobotCode Analyze",
)
@click.option(
    "-f",
    "--filter",
    "filter",
    metavar="PATTERN",
    type=str,
    multiple=True,
    help="""\
        Glob pattern to filter files to analyze. Can be specified multiple times.
        """,
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
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True, path_type=Path)
)
@pass_application
def code(
    app: Application,
    filter: Tuple[str],
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    paths: Tuple[Path],
) -> None:
    """\
        Performs static code analysis to detect syntax errors, missing keywords or variables,
        missing arguments, and more on the given *PATHS*. *PATHS* can be files or directories.
        If no PATHS are given, the current directory is used.
    """

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

        if variable:
            if robot_profile.variables is None:
                robot_profile.variables = {}
            for v in variable:
                name, value = v.split(":", 1) if ":" in v else (v, "")
                robot_profile.variables.update({name: value})

        if pythonpath:
            if robot_profile.python_path is None:
                robot_profile.python_path = []
            robot_profile.python_path.extend(pythonpath)

        if variablefile:
            if robot_profile.variable_files is None:
                robot_profile.variable_files = []
            for vf in variablefile:
                robot_profile.variable_files.append(vf)

        statistics = Statistic()
        for e in CodeAnalyzer(
            app=app,
            analysis_config=analyzer_config.to_workspace_analysis_config(),
            robot_profile=robot_profile,
            root_folder=root_folder,
        ).run(paths=paths, filter=filter):
            if isinstance(e, FolderDiagnosticReport):
                statistics.folders.add(e.folder)

                if e.items:
                    _print_diagnostics(app, root_folder, statistics, e.items, e.folder.uri.to_path())

            elif isinstance(e, DocumentDiagnosticReport):
                statistics.files.add(e.document)

                doc_path = (
                    e.document.uri.to_path().relative_to(root_folder) if root_folder else e.document.uri.to_path()
                )
                if e.items:
                    _print_diagnostics(app, root_folder, statistics, e.items, doc_path)

        statistics_str = str(statistics)
        if statistics.errors > 0:
            statistics_str = click.style(statistics_str, fg="red")

        app.echo(statistics_str)

        app.exit(statistics.errors)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


def _print_diagnostics(
    app: Application,
    root_folder: Optional[Path],
    statistics: Statistic,
    diagnostics: List[Diagnostic],
    folder_path: Optional[Path],
    print_range: bool = True,
) -> None:
    for item in diagnostics:
        severity = item.severity if item.severity is not None else DiagnosticSeverity.ERROR

        if severity == DiagnosticSeverity.ERROR:
            statistics.errors += 1
        elif severity == DiagnosticSeverity.WARNING:
            statistics.warnings += 1
        elif severity == DiagnosticSeverity.INFORMATION:
            statistics.infos += 1
        elif severity == DiagnosticSeverity.HINT:
            statistics.hints += 1

        app.echo(
            (
                (
                    f"{folder_path}:"
                    + (f"{item.range.start.line + 1}:{item.range.start.character + 1}: " if print_range else " ")
                )
                if folder_path and folder_path != root_folder
                else " "
            )
            + click.style(f"[{severity.name[0]}] {item.code}", fg=SEVERITY_COLORS[severity])
            + f": {indent(item.message, prefix='  ').strip()}",
        )

        if item.related_information:
            for related in item.related_information or []:
                related_path = try_get_relative_path(Uri(related.location.uri).to_path(), root_folder)

                app.echo(
                    f"    {related_path}:"
                    + (
                        f"{related.location.range.start.line + 1}:{related.location.range.start.character + 1}: "
                        if print_range
                        else " "
                    )
                    + f"{indent(related.message, prefix='      ').strip()}",
                )
