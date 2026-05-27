import functools
import hashlib
import time
from dataclasses import replace
from enum import Flag
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

import click

from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Range
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import as_json
from robotcode.core.utils.path import try_get_relative_path
from robotcode.core.workspace import WorkspaceFolder
from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.robot.config.loader import (
    load_robot_config_from_path,
)
from robotcode.robot.config.utils import get_config_files

from ..__version__ import __version__
from ..config import AnalyzeConfig, CacheConfig, CodeConfig, ExitCodeMask, ModifiersConfig
from ._models import CodeAnalysisResult, CodeAnalysisSummary
from ._sarif import (
    ArtifactLocation as SarifArtifactLocation,
)
from ._sarif import (
    Location as SarifLocation,
)
from ._sarif import (
    Message as SarifMessage,
)
from ._sarif import (
    PhysicalLocation as SarifPhysicalLocation,
)
from ._sarif import (
    Region as SarifRegion,
)
from ._sarif import (
    ReportingDescriptor as SarifReportingDescriptor,
)
from ._sarif import (
    Result as SarifResult,
)
from ._sarif import (
    Run as SarifRun,
)
from ._sarif import (
    SarifLog,
)
from ._sarif import (
    Tool as SarifTool,
)
from ._sarif import (
    ToolComponent as SarifToolComponent,
)
from .code_analyzer import CodeAnalyzer, DocumentDiagnosticReport, FolderDiagnosticReport

SEVERITY_COLORS = {
    DiagnosticSeverity.ERROR: "red",
    DiagnosticSeverity.WARNING: "yellow",
    DiagnosticSeverity.INFORMATION: "blue",
    DiagnosticSeverity.HINT: "cyan",
}

SEVERITY_NAMES = {
    DiagnosticSeverity.ERROR: "ERROR",
    DiagnosticSeverity.WARNING: "WARNING",
    DiagnosticSeverity.INFORMATION: "INFO",
    DiagnosticSeverity.HINT: "HINT",
}


class ReturnCode(Flag):
    SUCCESS = 0
    ERRORS = 1
    WARNINGS = 2
    INFOS = 4
    HINTS = 8


class ResultCollector:
    def __init__(
        self,
        exit_code_mask: ExitCodeMask,
        severities: Optional[Set[DiagnosticSeverity]] = None,
        codes: Optional[Set[str]] = None,
    ) -> None:
        self.exit_code_mask = exit_code_mask
        # When set, only diagnostics matching these filters are kept — affecting the output,
        # the summary counts and the exit code alike. Severity and code filters combine with AND.
        self._severities = severities
        self._codes = codes
        self._folders: Set[WorkspaceFolder] = set()
        self._files: Set[TextDocument] = set()
        self.diagnostics: List[Union[DocumentDiagnosticReport, FolderDiagnosticReport]] = []
        self._start_time = time.time()
        self._end_time = self._start_time

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(0.0, seconds)

        hours, remainder = divmod(total_seconds, 3600.0)
        minutes, seconds_remainder = divmod(remainder, 60.0)

        hours_int = int(hours)
        minutes_int = int(minutes)

        if hours_int > 0:
            return f"{hours_int}h {minutes_int}m {seconds_remainder:.2f}s"
        if minutes_int > 0:
            return f"{minutes_int}m {seconds_remainder:.2f}s"
        return f"{seconds_remainder:.2f}s"

    def start(self) -> float:
        self._start_time = time.time()
        return self._start_time

    def stop(self) -> float:
        self._end_time = time.time()
        return self._end_time

    @property
    def elapsed(self) -> float:
        return self._end_time - self._start_time

    @functools.cached_property
    def errors(self) -> int:
        return sum(
            len([i for i in e.items if i.severity == DiagnosticSeverity.ERROR]) for e in self.diagnostics if e.items
        )

    @functools.cached_property
    def warnings(self) -> int:
        return sum(
            len([i for i in e.items if i.severity == DiagnosticSeverity.WARNING]) for e in self.diagnostics if e.items
        )

    @functools.cached_property
    def infos(self) -> int:
        return sum(
            len([i for i in e.items if i.severity == DiagnosticSeverity.INFORMATION])
            for e in self.diagnostics
            if e.items
        )

    @functools.cached_property
    def hints(self) -> int:
        return sum(
            len([i for i in e.items if i.severity == DiagnosticSeverity.HINT]) for e in self.diagnostics if e.items
        )

    @property
    def files(self) -> int:
        return len(self._files)

    def _keep(self, diagnostic: Diagnostic) -> bool:
        if self._severities is not None:
            severity = diagnostic.severity if diagnostic.severity is not None else DiagnosticSeverity.ERROR
            if severity not in self._severities:
                return False
        if self._codes is not None:
            code = normalize_code(str(diagnostic.code)) if diagnostic.code is not None else None
            if code not in self._codes:
                return False
        return True

    def add_diagnostics_report(
        self, diagnostics_report: Union[DocumentDiagnosticReport, FolderDiagnosticReport]
    ) -> None:
        if self._severities is not None or self._codes is not None:
            diagnostics_report = replace(
                diagnostics_report, items=[d for d in diagnostics_report.items if self._keep(d)]
            )

        self.diagnostics.append(diagnostics_report)

        if isinstance(diagnostics_report, FolderDiagnosticReport):
            self._folders.add(diagnostics_report.folder)
        elif isinstance(diagnostics_report, DocumentDiagnosticReport):
            self._files.add(diagnostics_report.document)

    def __str__(self) -> str:
        return (
            f"Files: {len(self._files)}, Errors: {self.errors}, Warnings: {self.warnings}, "
            f"Infos: {self.infos}, Hints: {self.hints}"
            f" (in {self._format_duration(self.elapsed)})"
        )

    def calculate_return_code(self) -> ReturnCode:
        return_code = ReturnCode.SUCCESS
        if self.errors > 0 and not self.exit_code_mask & ExitCodeMask.ERROR:
            return_code |= ReturnCode.ERRORS
        if self.warnings > 0 and not self.exit_code_mask & ExitCodeMask.WARN:
            return_code |= ReturnCode.WARNINGS
        if self.infos > 0 and not self.exit_code_mask & ExitCodeMask.INFO:
            return_code |= ReturnCode.INFOS
        if self.hints > 0 and not self.exit_code_mask & ExitCodeMask.HINT:
            return_code |= ReturnCode.HINTS
        return return_code


def _parse_exit_code_mask(ctx: click.Context, param: click.Option, value: Tuple[str, ...]) -> ExitCodeMask:
    try:
        return ExitCodeMask.parse(value)
    except KeyError as e:
        raise click.BadParameter(str(e)) from e


_SEVERITY_BY_NAME = {
    "error": DiagnosticSeverity.ERROR,
    "warn": DiagnosticSeverity.WARNING,
    "warning": DiagnosticSeverity.WARNING,
    "info": DiagnosticSeverity.INFORMATION,
    "information": DiagnosticSeverity.INFORMATION,
    "hint": DiagnosticSeverity.HINT,
}


def _parse_severities(
    ctx: click.Context, param: click.Option, value: Tuple[str, ...]
) -> Optional[Set[DiagnosticSeverity]]:
    """Parse repeated/comma-separated --severity values into a set, or None when unset."""
    result: Set[DiagnosticSeverity] = set()
    for entry in value:
        for part_orig in entry.split(","):
            part = part_orig.strip().lower()
            if not part:
                continue
            severity = _SEVERITY_BY_NAME.get(part)
            if severity is None:
                raise click.BadParameter(f"invalid severity: {part_orig}")
            result.add(severity)
    return result or None


# Same normalization the diagnostic modifiers use, so `--code keyword-not-found`,
# `KeywordNotFound` and `keywordnotfound` all match.
_CODE_TRANSLATION = str.maketrans("", "", "_- ")


def normalize_code(code: str) -> str:
    return code.translate(_CODE_TRANSLATION).lower()


def _parse_codes(ctx: click.Context, param: click.Option, value: Tuple[str, ...]) -> Optional[Set[str]]:
    """Parse repeated/comma-separated --code values into a normalized set, or None when unset."""
    result: Set[str] = set()
    for entry in value:
        for part_orig in entry.split(","):
            part = normalize_code(part_orig.strip())
            if part:
                result.add(part)
    return result or None


def _validate_load_library_timeout(ctx: click.Context, param: click.Option, value: Optional[int]) -> Optional[int]:
    """Validate --load-library-timeout (>0) or pass through None."""
    if value is None:
        return None
    if value <= 0:
        raise click.BadParameter("must be > 0")
    return value


@click.command(
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
    "filter_patterns",
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
@click.option(
    "--exit-code-mask",
    "-xm",
    multiple=True,
    callback=_parse_exit_code_mask,
    metavar="[" + "|".join(member.name.lower() for member in ExitCodeMask if member.name is not None) + "|all]",
    help="Specifies which diagnostic severities should not affect the exit code. "
    "For example, with 'warn' in the mask, warnings won't cause a non-zero exit code.",
)
@click.option(
    "--extend-exit-code-mask",
    "-xe",
    multiple=True,
    callback=_parse_exit_code_mask,
    metavar="[" + "|".join(member.name.lower() for member in ExitCodeMask if member.name is not None) + "|all]",
    help="Extend the exit code mask with the specified values. This appends to the default mask, defined in the config"
    " file.",
)
@click.option(
    "--severity",
    multiple=True,
    callback=_parse_severities,
    metavar="[error|warn|warning|info|information|hint]",
    help="Only report diagnostics of these severities. Repeatable and comma-separated. "
    "Filtered-out severities are ignored entirely — they don't appear in the output, the summary or the exit code. "
    "When omitted, all severities are reported.",
)
@click.option(
    "--code",
    "codes",
    multiple=True,
    callback=_parse_codes,
    metavar="CODE",
    help="Only report diagnostics with these codes (e.g. `KeywordNotFound`). Repeatable and comma-separated; "
    "matching is case-insensitive. Unlike the modifiers, this filters without changing severity. "
    "Combined with --severity, both must match. When omitted, all codes are reported.",
)
@click.option(
    "--load-library-timeout",
    type=int,
    callback=_validate_load_library_timeout,
    metavar="SECONDS",
    show_envvar=True,
    envvar="ROBOTCODE_LOAD_LIBRARY_TIMEOUT",
    help=(
        "Timeout (in seconds) for loading libraries and variable files during analysis. "
        "Must be > 0. Overrides config file and environment variable when set."
    ),
)
@click.option(
    "--collect-unused/--no-collect-unused",
    default=None,
    help="Enable or disable collection of unused keyword and unused variable diagnostics. "
    "Overrides the config file setting when specified.",
)
@click.option(
    "--cache-namespaces/--no-cache-namespaces",
    default=None,
    help="Enable or disable caching of fully analyzed namespace data to disk. "
    "Can speed up startup for large projects by skipping re-analysis of unchanged files.",
)
@click.option(
    "--show-tracebacks/--no-show-tracebacks",
    default=False,
    help="Include the full diagnostic message in the text output, including Python tracebacks and PYTHONPATH "
    "listings that Robot Framework appends to import errors. Off by default to keep output concise. "
    "Has no effect on JSON output, which always carries the full message.",
)
@click.option(
    "--full-paths/--no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of paths relative to the project root. Applies to both text and JSON output.",
)
@click.option(
    "--output-format",
    type=click.Choice(["concise", "json", "json-indent", "sarif", "github", "gitlab"]),
    default=None,
    help="Output format for the analysis result. Overrides the global `--format` for this command. "
    "`concise` (default) is the human-readable text output; `sarif` emits a SARIF 2.1.0 log; "
    "`github` emits GitHub Actions workflow annotations; `gitlab` emits a GitLab Code Quality report.",
)
@click.option(
    "--output-file",
    "output_file",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write the report to FILE instead of stdout. Useful with `--output-format sarif`/`gitlab` "
    "to produce an artifact for CI upload.",
)
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True, path_type=Path)
)
@pass_application
def code(
    app: Application,
    filter_patterns: Tuple[str, ...],
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    modifiers_ignore: Tuple[str, ...],
    modifiers_error: Tuple[str, ...],
    modifiers_warning: Tuple[str, ...],
    modifiers_information: Tuple[str, ...],
    modifiers_hint: Tuple[str, ...],
    exit_code_mask: ExitCodeMask,
    extend_exit_code_mask: ExitCodeMask,
    severity: Optional[Set[DiagnosticSeverity]],
    codes: Optional[Set[str]],
    paths: Tuple[Path, ...],
    load_library_timeout: Optional[int],
    collect_unused: Optional[bool],
    cache_namespaces: Optional[bool],
    show_tracebacks: bool,
    full_paths: bool,
    output_format: Optional[str],
    output_file: Optional[Path],
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

        default_mask = (
            exit_code_mask
            if exit_code_mask != ExitCodeMask.NONE
            else ExitCodeMask.parse(analyzer_config.code.exit_code_mask if analyzer_config.code is not None else None)
        )
        mask = default_mask | extend_exit_code_mask

        if load_library_timeout is not None:
            analyzer_config.load_library_timeout = load_library_timeout

        if collect_unused is not None:
            if analyzer_config.code is None:
                analyzer_config.code = CodeConfig()
            analyzer_config.code.collect_unused = collect_unused

        if cache_namespaces is not None:
            if analyzer_config.cache is None:
                analyzer_config.cache = CacheConfig()
            analyzer_config.cache.cache_namespaces = cache_namespaces

        app.verbose(f"Using analyzer_config: {analyzer_config}")
        app.verbose(f"Using exit code mask: {mask}")

        result_collector = ResultCollector(mask, severities=severity, codes=codes)
        result_collector.start()
        analyzer = CodeAnalyzer(
            app=app,
            analysis_config=analyzer_config.to_workspace_analysis_config(),
            robot_profile=robot_profile,
            root_folder=root_folder,
            collect_unused=bool(
                analyzer_config.code.collect_unused
                if analyzer_config.code is not None and analyzer_config.code.collect_unused is not None
                else False
            ),
        )
        try:
            for e in analyzer.run(paths=paths, filter_patterns=filter_patterns):
                result_collector.add_diagnostics_report(e)
        finally:
            result_collector.stop()

        folder_entries, sorted_documents = _collect_sorted_diagnostics(
            result_collector.diagnostics, root_folder, full_paths
        )

        # The local --output-format wins over the global --format; default is concise text.
        resolved_format = output_format or {
            OutputFormat.JSON: "json",
            OutputFormat.JSON_INDENT: "json-indent",
            OutputFormat.TOML: "toml",
        }.get(app.config.output_format or OutputFormat.TEXT, "concise")

        if output_file is not None and resolved_format in ("concise", "toml"):
            raise click.UsageError(
                "--output-file is only supported with the json, json-indent, sarif, github or gitlab formats."
            )

        summary = CodeAnalysisSummary(
            files=result_collector.files,
            errors=result_collector.errors,
            warnings=result_collector.warnings,
            infos=result_collector.infos,
            hints=result_collector.hints,
        )

        if resolved_format == "concise":
            for folder_path, items in folder_entries:
                _print_diagnostics(
                    app, root_folder, items, folder_path, print_range=False, show_tracebacks=show_tracebacks
                )
            for doc_path, items in sorted_documents.items():
                _print_diagnostics(app, root_folder, items, doc_path, show_tracebacks=show_tracebacks)

            statistics_str = str(result_collector)
            for count, sev in (
                (result_collector.errors, DiagnosticSeverity.ERROR),
                (result_collector.warnings, DiagnosticSeverity.WARNING),
                (result_collector.infos, DiagnosticSeverity.INFORMATION),
                (result_collector.hints, DiagnosticSeverity.HINT),
            ):
                if count > 0:
                    statistics_str = click.style(statistics_str, fg=SEVERITY_COLORS[sev])
                    break

            app.echo(statistics_str)
        elif resolved_format == "sarif":
            text = as_json(
                build_sarif_log(folder_entries, sorted_documents, root_folder, full_paths, __version__), indent=True
            )
            _write_or_echo(app, text, output_file)
        elif resolved_format == "github":
            _write_or_echo(app, "\n".join(build_github_annotations(folder_entries, sorted_documents)), output_file)
        elif resolved_format == "gitlab":
            report = build_gitlab_report(folder_entries, sorted_documents)
            _write_or_echo(app, as_json(report, indent=True), output_file)
        elif output_file is not None:
            # json / json-indent written to a file (always plain, no color/pager).
            result = _build_analysis_result(folder_entries, sorted_documents, summary)
            _write_or_echo(app, as_json(result, indent=resolved_format == "json-indent"), output_file)
        else:
            # json / json-indent / toml on stdout via the shared renderer (keeps color/paging).
            app.print_data(
                _build_analysis_result(folder_entries, sorted_documents, summary),
                remove_defaults=True,
                default_output_format={
                    "json": OutputFormat.JSON,
                    "json-indent": OutputFormat.JSON_INDENT,
                    "toml": OutputFormat.TOML,
                }.get(resolved_format),
            )

        app.exit(result_collector.calculate_return_code().value, fast=True)

    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e


def _write_or_echo(app: Application, text: str, output_path: Optional[Path]) -> None:
    if output_path is None:
        app.echo(text)
        return

    if not output_path.parent.exists():
        raise click.UsageError(f"Cannot write to '{output_path}': the directory '{output_path.parent}' does not exist.")
    try:
        output_path.write_text(text + "\n", encoding="utf-8")
    except OSError as e:
        raise click.ClickException(f"Could not write output to '{output_path}': {e}") from e
    app.verbose(f"Wrote output to {output_path}")


def _display_path(path: Path, root_folder: Optional[Path], full_paths: bool) -> Path:
    return path if full_paths else try_get_relative_path(path, root_folder)


def _collect_sorted_diagnostics(
    reports: Iterable[Union[DocumentDiagnosticReport, FolderDiagnosticReport]],
    root_folder: Optional[Path],
    full_paths: bool,
) -> Tuple[List[Tuple[Path, List[Diagnostic]]], Dict[Path, List[Diagnostic]]]:
    """Split reports into folder-level and per-document diagnostics, keyed by display path.

    Folder-level reports keep their original order; document diagnostics are merged per
    file and sorted by (line, column) so the output is stable regardless of analyzer pass
    order. `full_paths` selects absolute vs. root-relative display paths.
    """

    def display_path(path: Path) -> Path:
        return _display_path(path, root_folder, full_paths)

    folder_entries: List[Tuple[Path, List[Diagnostic]]] = [
        (display_path(e.folder.uri.to_path()), e.items)
        for e in reports
        if isinstance(e, FolderDiagnosticReport) and e.items
    ]

    documents_to_items: Dict[Path, List[Diagnostic]] = {}
    for e in reports:
        if isinstance(e, DocumentDiagnosticReport) and e.items:
            documents_to_items.setdefault(display_path(e.document.uri.to_path()), []).extend(e.items)

    sorted_documents = {
        doc_path: sorted(documents_to_items[doc_path], key=lambda d: (d.range.start.line, d.range.start.character))
        for doc_path in sorted(documents_to_items)
    }

    return folder_entries, sorted_documents


def _build_analysis_result(
    folder_entries: List[Tuple[Path, List[Diagnostic]]],
    sorted_documents: Dict[Path, List[Diagnostic]],
    summary: CodeAnalysisSummary,
) -> CodeAnalysisResult:
    """Build the JSON result model. Paths are rendered as POSIX strings so the
    output is stable across platforms; workspace-level reports key on `.`."""
    diagnostics_by_source: Dict[str, List[Diagnostic]] = {path.as_posix(): items for path, items in folder_entries}
    for doc_path, items in sorted_documents.items():
        diagnostics_by_source.setdefault(doc_path.as_posix(), []).extend(items)
    return CodeAnalysisResult(diagnostics=diagnostics_by_source, summary=summary)


# LSP severities collapse onto SARIF's four levels (it has no dedicated "hint").
_SARIF_LEVELS = {
    DiagnosticSeverity.ERROR: "error",
    DiagnosticSeverity.WARNING: "warning",
    DiagnosticSeverity.INFORMATION: "note",
    DiagnosticSeverity.HINT: "note",
}


def _sarif_region(rng: Range) -> SarifRegion:
    # LSP ranges are 0-based; SARIF regions are 1-based.
    return SarifRegion(
        start_line=rng.start.line + 1,
        start_column=rng.start.character + 1,
        end_line=rng.end.line + 1,
        end_column=rng.end.character + 1,
    )


def _fingerprint(uri: str, rule_id: str, message: str, occurrence: int) -> str:
    # Deliberately excludes line/column so an alert survives unrelated edits that
    # shift it; `occurrence` disambiguates identical findings in the same file.
    raw = f"{uri}\x00{rule_id}\x00{message}\x00{occurrence}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_sarif_log(
    folder_entries: List[Tuple[Path, List[Diagnostic]]],
    sorted_documents: Dict[Path, List[Diagnostic]],
    root_folder: Optional[Path],
    full_paths: bool,
    version: str,
) -> SarifLog:
    """Map collected diagnostics to a SARIF 2.1.0 log.

    Rules are emitted dynamically for the codes that actually occur. Locations use
    POSIX URIs (relative to the project root unless `full_paths`), which is what
    GitHub code scanning expects. Workspace-level diagnostics key on `.`.
    """
    rules: List[SarifReportingDescriptor] = []
    rule_index: Dict[str, int] = {}
    results: List[SarifResult] = []
    fingerprint_seen: Dict[Tuple[str, str, str], int] = {}

    def index_of_rule(rule_id: str) -> int:
        if rule_id not in rule_index:
            rule_index[rule_id] = len(rules)
            rules.append(SarifReportingDescriptor(id=rule_id, name=rule_id))
        return rule_index[rule_id]

    def related_locations(diag: Diagnostic) -> Optional[List[SarifLocation]]:
        if not diag.related_information:
            return None
        locations = []
        for related in diag.related_information:
            rel_uri = _display_path(Uri(related.location.uri).to_path(), root_folder, full_paths).as_posix()
            locations.append(
                SarifLocation(
                    physical_location=SarifPhysicalLocation(
                        artifact_location=SarifArtifactLocation(uri=rel_uri),
                        region=_sarif_region(related.location.range),
                    ),
                    message=SarifMessage(text=related.message) if related.message else None,
                )
            )
        return locations

    def add_result(uri: str, diag: Diagnostic) -> None:
        rule_id = str(diag.code) if diag.code is not None else "robotcode"
        severity = diag.severity if diag.severity is not None else DiagnosticSeverity.ERROR

        occurrence_key = (uri, rule_id, diag.message)
        occurrence = fingerprint_seen.get(occurrence_key, 0)
        fingerprint_seen[occurrence_key] = occurrence + 1

        results.append(
            SarifResult(
                rule_id=rule_id,
                rule_index=index_of_rule(rule_id),
                level=_SARIF_LEVELS[severity],
                message=SarifMessage(text=diag.message),
                locations=[
                    SarifLocation(
                        physical_location=SarifPhysicalLocation(
                            artifact_location=SarifArtifactLocation(uri=uri),
                            region=_sarif_region(diag.range),
                        )
                    )
                ],
                related_locations=related_locations(diag),
                partial_fingerprints={"robotcode/v1": _fingerprint(uri, rule_id, diag.message, occurrence)},
            )
        )

    for path, items in folder_entries:
        for diag in items:
            add_result(path.as_posix(), diag)
    for doc_path, items in sorted_documents.items():
        for diag in items:
            add_result(doc_path.as_posix(), diag)

    return SarifLog(
        runs=[
            SarifRun(
                tool=SarifTool(
                    driver=SarifToolComponent(
                        name="RobotCode",
                        version=version,
                        information_uri="https://robotcode.io",
                        rules=rules,
                    )
                ),
                results=results,
            )
        ]
    )


def _all_entries(
    folder_entries: List[Tuple[Path, List[Diagnostic]]],
    sorted_documents: Dict[Path, List[Diagnostic]],
) -> Iterable[Tuple[Path, List[Diagnostic]]]:
    yield from folder_entries
    yield from sorted_documents.items()


# GitHub Actions workflow command per severity (it has no dedicated hint level).
_GITHUB_COMMANDS = {
    DiagnosticSeverity.ERROR: "error",
    DiagnosticSeverity.WARNING: "warning",
    DiagnosticSeverity.INFORMATION: "notice",
    DiagnosticSeverity.HINT: "notice",
}


def _gh_escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _gh_escape_property(value: str) -> str:
    return _gh_escape_data(value).replace(":", "%3A").replace(",", "%2C")


def build_github_annotations(
    folder_entries: List[Tuple[Path, List[Diagnostic]]],
    sorted_documents: Dict[Path, List[Diagnostic]],
) -> List[str]:
    """Render diagnostics as GitHub Actions workflow command annotations.

    Lines look like `::error file=...,line=...,col=...,title=Code::message`. Positions
    are 1-based; values are escaped per the @actions/toolkit rules.
    """
    lines: List[str] = []
    for path, items in _all_entries(folder_entries, sorted_documents):
        uri = path.as_posix()
        for diag in items:
            severity = diag.severity if diag.severity is not None else DiagnosticSeverity.ERROR
            props = [
                f"file={_gh_escape_property(uri)}",
                f"line={diag.range.start.line + 1}",
                f"endLine={diag.range.end.line + 1}",
                f"col={diag.range.start.character + 1}",
                f"endColumn={diag.range.end.character + 1}",
            ]
            if diag.code is not None:
                props.append(f"title={_gh_escape_property(str(diag.code))}")
            lines.append(f"::{_GITHUB_COMMANDS[severity]} {','.join(props)}::{_gh_escape_data(diag.message)}")
    return lines


# GitLab Code Quality severity (info | minor | major | critical | blocker).
_GITLAB_SEVERITIES = {
    DiagnosticSeverity.ERROR: "major",
    DiagnosticSeverity.WARNING: "minor",
    DiagnosticSeverity.INFORMATION: "info",
    DiagnosticSeverity.HINT: "info",
}


def build_gitlab_report(
    folder_entries: List[Tuple[Path, List[Diagnostic]]],
    sorted_documents: Dict[Path, List[Diagnostic]],
) -> List[Dict[str, Any]]:
    """Render diagnostics as a GitLab Code Quality report (a JSON array).

    Field names are snake_case as required by GitLab (so this uses plain dicts, not
    the CamelSnakeMixin models). Each entry carries a stable fingerprint.
    """
    report: List[Dict[str, Any]] = []
    fingerprint_seen: Dict[Tuple[str, str, str], int] = {}
    for path, items in _all_entries(folder_entries, sorted_documents):
        uri = path.as_posix()
        for diag in items:
            severity = diag.severity if diag.severity is not None else DiagnosticSeverity.ERROR
            check_name = str(diag.code) if diag.code is not None else "robotcode"
            key = (uri, check_name, diag.message)
            occurrence = fingerprint_seen.get(key, 0)
            fingerprint_seen[key] = occurrence + 1
            report.append(
                {
                    "description": diag.message,
                    "check_name": check_name,
                    "fingerprint": _fingerprint(uri, check_name, diag.message, occurrence),
                    "severity": _GITLAB_SEVERITIES[severity],
                    "location": {"path": uri, "lines": {"begin": diag.range.start.line + 1}},
                }
            )
    return report


# Markers that Robot Framework appends to error messages for debugging.
# In default mode they get trimmed; with -v / --verbose they stay.
_DEBUG_SECTION_MARKERS = ("Traceback (most recent call last):", "PYTHONPATH:")


def _trim_debug_sections(message: str) -> str:
    """Cut a Robot Framework error message at the first debug section marker."""
    kept: List[str] = []
    for line in message.split("\n"):
        if any(line.lstrip().startswith(m) for m in _DEBUG_SECTION_MARKERS):
            break
        kept.append(line)
    return "\n".join(kept).rstrip()


def _normalize_indent(message: str, indent: str) -> str:
    """Normalize a multi-line message: keep the first line as-is, re-indent every
    subsequent non-empty line with the given prefix (replacing whatever indent the
    source string had). Empty lines are dropped."""
    lines = message.splitlines()
    if not lines:
        return ""
    head = lines[0].strip()
    tail = [f"{indent}{line.strip()}" for line in lines[1:] if line.strip()]
    return "\n".join([head, *tail])


def _print_diagnostics(
    app: Application,
    root_folder: Optional[Path],
    diagnostics: List[Diagnostic],
    folder_path: Optional[Path],
    print_range: bool = True,
    show_tracebacks: bool = False,
) -> None:
    for item in diagnostics:
        severity = item.severity if item.severity is not None else DiagnosticSeverity.ERROR
        message = item.message if show_tracebacks else _trim_debug_sections(item.message)

        app.echo(
            (
                (
                    f"{folder_path}:"
                    + (f"{item.range.start.line + 1}:{item.range.start.character + 1}: " if print_range else " ")
                )
                if folder_path
                else ""
            )
            + click.style(f"[{SEVERITY_NAMES[severity]}] {item.code}", fg=SEVERITY_COLORS[severity])
            + f": {_normalize_indent(message, '    ')}",
        )

        if item.related_information:
            for related in item.related_information or []:
                related_path = try_get_relative_path(Uri(related.location.uri).to_path(), root_folder)
                related_message = related.message if show_tracebacks else _trim_debug_sections(related.message)
                rendered = _normalize_indent(related_message, "        ") or "(see related location)"

                app.echo(
                    f"    -> {related_path}:"
                    f"{related.location.range.start.line + 1}:{related.location.range.start.character + 1}: "
                    f"{rendered}",
                )
