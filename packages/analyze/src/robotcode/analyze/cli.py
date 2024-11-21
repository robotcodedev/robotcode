from enum import Flag
from pathlib import Path
from textwrap import indent
from typing import List, Optional, Set, Tuple, Union

import click

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
from .config import AnalyzeConfig, ModifiersConfig


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


class ReturnCode(Flag):
    SUCCESS = 0
    ERRORS = 1
    WARNINGS = 2
    INFOS = 4
    HINTS = 8


class Statistic:
    def __init__(self) -> None:
        self._folders: Set[WorkspaceFolder] = set()
        self._files: Set[TextDocument] = set()
        self._diagnostics: List[Union[DocumentDiagnosticReport, FolderDiagnosticReport]] = []

    @property
    def errors(self) -> int:
        return sum(
            len([i for i in e.items if i.severity == DiagnosticSeverity.ERROR]) for e in self._diagnostics if e.items
        )

    @property
    def warnings(self) -> int:
        return sum(
            len([i for i in e.items if i.severity == DiagnosticSeverity.WARNING]) for e in self._diagnostics if e.items
        )

    @property
    def infos(self) -> int:
        return sum(
            len([i for i in e.items if i.severity == DiagnosticSeverity.INFORMATION])
            for e in self._diagnostics
            if e.items
        )

    @property
    def hints(self) -> int:
        return sum(
            len([i for i in e.items if i.severity == DiagnosticSeverity.HINT]) for e in self._diagnostics if e.items
        )

    def add_diagnostics_report(
        self, diagnostics_report: Union[DocumentDiagnosticReport, FolderDiagnosticReport]
    ) -> None:
        self._diagnostics.append(diagnostics_report)

        if isinstance(diagnostics_report, FolderDiagnosticReport):
            self._folders.add(diagnostics_report.folder)
        elif isinstance(diagnostics_report, DocumentDiagnosticReport):
            self._files.add(diagnostics_report.document)

    def __str__(self) -> str:
        return (
            f"Files: {len(self._files)}, Errors: {self.errors}, Warnings: {self.warnings}, "
            f"Infos: {self.infos}, Hints: {self.hints}"
        )

    def calculate_return_code(self) -> ReturnCode:
        return_code = ReturnCode.SUCCESS
        if self.errors > 0:
            return_code |= ReturnCode.ERRORS
        if self.warnings > 0:
            return_code |= ReturnCode.WARNINGS
        if self.infos > 0:
            return_code |= ReturnCode.INFOS
        if self.hints > 0:
            return_code |= ReturnCode.HINTS
        return return_code


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
@click.option(
    "-mi",
    "--modifiers-ignore",
    metavar="CODE",
    type=str,
    multiple=True,
    help="Specifies the diagnostics codes to ignore.",
)
@click.option(
    "-me",
    "--modifiers-error",
    metavar="CODE",
    type=str,
    multiple=True,
    help="Specifies the diagnostics codes to treat as errors.",
)
@click.option(
    "-mw",
    "--modifiers-warning",
    metavar="CODE",
    type=str,
    multiple=True,
    help="Specifies the diagnostics codes to treat as warning.",
)
@click.option(
    "-mI",
    "--modifiers-information",
    metavar="CODE",
    type=str,
    multiple=True,
    help="Specifies the diagnostics codes to treat as information.",
)
@click.option(
    "-mh",
    "--modifiers-hint",
    metavar="CODE",
    type=str,
    multiple=True,
    help="Specifies the diagnostics codes to treat as hint.",
)
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True, path_type=Path)
)
@pass_application
def code(
    app: Application,
    filter: Tuple[str, ...],
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    modifiers_ignore: Tuple[str, ...],
    modifiers_error: Tuple[str, ...],
    modifiers_warning: Tuple[str, ...],
    modifiers_information: Tuple[str, ...],
    modifiers_hint: Tuple[str, ...],
    paths: Tuple[Path],
) -> None:
    """\
        Performs static code analysis to identify potential issues in the specified *PATHS*. The analysis detects syntax
        errors, missing keywords or variables, missing arguments, and other problems.

        - **PATHS**: Can be individual files or directories. If no *PATHS* are provided, the current directory is
          analyzed by default.

        The return code is a bitwise combination of the following values:

        - `0`: **SUCCESS** - No issues detected.
        - `1`: **ERRORS** - Critical issues found.
        - `2`: **WARNINGS** - Non-critical issues detected.
        - `4`: **INFORMATIONS** - General information messages.
        - `8`: **HINTS** - Suggestions or improvements.

        \b
        *Examples*:
        ```
        robotcode analyze code
        robotcode analyze code --filter **/*.robot
        robotcode analyze code tests/acceptance/first.robot
        robotcode analyze code -mi DuplicateKeyword tests/acceptance/first.robot
        robotcode --format json analyze code
        ```
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

        if analyzer_config.modifiers is None:
            analyzer_config.modifiers = ModifiersConfig()

        if modifiers_ignore:
            if analyzer_config.modifiers.ignore is None:
                analyzer_config.modifiers.ignore = []
            analyzer_config.modifiers.ignore.extend(modifiers_ignore)

        if modifiers_error:
            if analyzer_config.modifiers.error is None:
                analyzer_config.modifiers.error = []
            analyzer_config.modifiers.error.extend(modifiers_error)

        if modifiers_warning:
            if analyzer_config.modifiers.warning is None:
                analyzer_config.modifiers.warning = []
            analyzer_config.modifiers.warning.extend(modifiers_warning)

        if modifiers_information:
            if analyzer_config.modifiers.information is None:
                analyzer_config.modifiers.information = []
            analyzer_config.modifiers.information.extend(modifiers_information)

        if modifiers_hint:
            if analyzer_config.modifiers.hint is None:
                analyzer_config.modifiers.hint = []
            analyzer_config.modifiers.hint.extend(modifiers_hint)

        statistics = Statistic()
        for e in CodeAnalyzer(
            app=app,
            analysis_config=analyzer_config.to_workspace_analysis_config(),
            robot_profile=robot_profile,
            root_folder=root_folder,
        ).run(paths=paths, filter=filter):
            statistics.add_diagnostics_report(e)

            if isinstance(e, FolderDiagnosticReport):
                if e.items:
                    _print_diagnostics(app, root_folder, e.items, e.folder.uri.to_path())
            elif isinstance(e, DocumentDiagnosticReport):
                doc_path = (
                    e.document.uri.to_path().relative_to(root_folder) if root_folder else e.document.uri.to_path()
                )
                if e.items:
                    _print_diagnostics(app, root_folder, e.items, doc_path)

        statistics_str = str(statistics)
        if statistics.errors > 0:
            statistics_str = click.style(statistics_str, fg="red")

        app.echo(statistics_str)

        app.exit(statistics.calculate_return_code().value)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


def _print_diagnostics(
    app: Application,
    root_folder: Optional[Path],
    diagnostics: List[Diagnostic],
    folder_path: Optional[Path],
    print_range: bool = True,
) -> None:
    for item in diagnostics:
        severity = item.severity if item.severity is not None else DiagnosticSeverity.ERROR

        app.echo(
            (
                (
                    f"{folder_path}:"
                    + (f"{item.range.start.line + 1}:{item.range.start.character + 1}: " if print_range else " ")
                )
                if folder_path and folder_path != root_folder
                else ""
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
