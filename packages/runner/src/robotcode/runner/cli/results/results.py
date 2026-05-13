"""`robotcode results` — inspect Robot Framework result files.

Subcommands:
- `summary`: headline counts + status for a finished run.
- `show`: list individual tests with status / message filters.
- `log`: per-test keyword and message tree; can extract referenced artefacts.

All subcommands respect the global `-f/--format` option:
- TEXT (default) renders via `app.echo_via_pager` using click.style — same
  visual style as `robotcode discover` (bold names, blue labels, colored
  status badges, `(path:line)` suffix for VS Code's terminal link detector).
- JSON/JSON-INDENT/TOML go through `app.print_data` with the dataclass schema
  defined in `_models`.
"""

import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

import click
from robot.errors import DataError

from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.utils import get_config_files
from robotcode.robot.utils import RF_VERSION

from . import _html, _render
from ._models import (
    ArtifactRef,
    Counts,
    LogEntry,
    LogResult,
    LogTest,
    ResultFileInfo,
    ShowResult,
    SummaryResult,
    TestResultItem,
)

_STATUS_KEY_MAP = {
    "pass": "PASS",
    "fail": "FAIL",
    "skip": "SKIP",
    "not-run": "NOT RUN",
    "not_run": "NOT RUN",
}


RESULT_FILTER_OPTIONS = [
    click.option(
        "--status",
        "status_filters",
        multiple=True,
        type=click.Choice(["pass", "fail", "skip", "not-run"], case_sensitive=False),
        help="Only include tests with one of these statuses. Repeat to add more (OR).",
    ),
    click.option(
        "-i",
        "--include",
        "include_tags",
        multiple=True,
        metavar="TAG_PATTERN",
        help=(
            "Include tests matching the tag pattern. Supports Robot's tag pattern "
            "syntax (AND, OR, NOT, *, ?). Repeat for additional patterns (OR-joined)."
        ),
    ),
    click.option(
        "-e",
        "--exclude",
        "exclude_tags",
        multiple=True,
        metavar="TAG_PATTERN",
        help="Exclude tests matching the tag pattern. Same syntax as --include.",
    ),
    click.option(
        "-s",
        "--suite",
        "suite_globs",
        multiple=True,
        metavar="NAME",
        help="Only include tests inside the named suite (glob against full suite name).",
    ),
    click.option(
        "-t",
        "--test",
        "--task",
        "test_globs",
        multiple=True,
        metavar="NAME",
        help=(
            "Only include tests whose name matches (glob against full test name). "
            "`--task` is an alias for `--test` (Robot's RPA terminology)."
        ),
    ),
]


OUTPUT_OPTION = click.option(
    "-o",
    "--output",
    "output_file",
    type=click.Path(path_type=Path),
    default=None,
    metavar="PATH",
    help=(
        "Path to output.xml/output.json (Robot's `--output`). If omitted, "
        "auto-discovered from the active profile's `output_dir` + `output` "
        "settings (with timestamp glob fallback and ./output.xml as last "
        "resort). A directory may also be passed — then auto-discovery "
        "happens inside it."
    ),
)


@click.group(invoke_without_command=False)
def results() -> None:
    """\
    Inspect a finished run's `output.xml` / `output.json` — counts,
    failures, and per-test execution tree, without re-running.

    The result file is auto-discovered from the active profile's
    `output_dir` / `output` settings; override with `-o/--output PATH`.
    Use `-f json` (or `toml`) for a structured payload.

    \b
    Examples:
    ```
    robotcode results summary
    robotcode results summary --failures
    robotcode results show --status fail
    robotcode results log "*Login*"
    robotcode --format json results summary
    ```
    """


@results.command()
@add_options(*RESULT_FILTER_OPTIONS, OUTPUT_OPTION)
@click.option(
    "--failures/--no-failures",
    "show_failures",
    default=False,
    show_default=True,
    help="Include the list of failed tests (with messages) above the counts table.",
)
@click.option(
    "--full-paths/--no-full-paths",
    default=False,
    show_default=True,
    help="Show absolute source paths instead of paths relative to cwd.",
)
@pass_application
def summary(
    app: Application,
    status_filters: Tuple[str, ...],
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
    output_file: Optional[Path],
    show_failures: bool,
    full_paths: bool,
) -> None:
    """\
    Print headline counts and overall status for a finished run.

    Pass `--failures` to also list failed tests above the counts.
    Filter options narrow what is counted.

    \b
    Examples:
    ```
    robotcode results summary
    robotcode results summary --failures
    robotcode results summary -i smoke --status fail
    robotcode --format json results summary
    ```
    """
    profile, root_folder = _resolve_profile(app)
    with app.chdir(root_folder):
        path = _resolve_output_file(app, profile, output_file)
        execution = _load_execution_result(path)

        filters_active = bool(status_filters or include_tags or exclude_tags or suite_globs or test_globs)
        if include_tags or exclude_tags or suite_globs or test_globs:
            _apply_tree_filters(execution.suite, include_tags, exclude_tags, suite_globs, test_globs)
        counts = _collect_counts(execution.suite, status_filters)
        failures = _collect_failures(execution.suite, status_filters, full_paths=full_paths) if show_failures else None
        exec_msg_counts = _count_execution_messages(getattr(execution, "errors", None))
        msg_counts = _count_all_messages(execution)

        data = SummaryResult(
            file=_make_file_info(path),
            status=execution.suite.status,
            counts=counts,
            elapsed_seconds=_elapsed_seconds(execution.suite),
            start_time=_iso(getattr(execution.suite, "start_time", None)),
            end_time=_iso(getattr(execution.suite, "end_time", None)),
            failures=failures or None,
            messages_count=msg_counts or None,
            execution_messages_count=exec_msg_counts or None,
            filters_applied=_filters_dict(status_filters, include_tags, exclude_tags, suite_globs, test_globs)
            if filters_active
            else None,
        )

        if app.config.output_format in (None, OutputFormat.TEXT):
            app.echo_via_pager(_render.render_summary(data, full_paths=full_paths))
        else:
            app.print_data(data, remove_defaults=True)


@results.command()
@add_options(*RESULT_FILTER_OPTIONS, OUTPUT_OPTION)
@click.option(
    "--top",
    "top_n",
    type=click.IntRange(min=0),
    default=0,
    show_default=True,
    help="Show at most N tests (0 = no limit, default).",
)
@click.option(
    "--message-chars",
    type=click.IntRange(min=0),
    default=120,
    show_default=True,
    help="Truncate each message to N characters (0 = no truncation).",
)
@click.option(
    "--full-paths/--no-full-paths",
    default=False,
    show_default=True,
    help="Show absolute source paths instead of paths relative to cwd.",
)
@click.option(
    "--tags/--no-tags",
    "show_tags",
    default=False,
    show_default=True,
    help="Append the tag list after each test.",
)
@click.option(
    "--timing/--no-timing",
    "show_timing",
    default=True,
    show_default=True,
    help=(
        "Show start time per test and append start / end / elapsed of the "
        "run to the statistics block. Use `--no-timing` to suppress."
    ),
)
@click.option(
    "--sort",
    "sort_field",
    type=click.Choice(["name", "status", "elapsed", "start", "suite"], case_sensitive=False),
    default=None,
    metavar="FIELD",
    help=(
        "Sort tests before display. `name`/`suite` = lexicographic full-name/suite. "
        "`status` = FAIL → SKIP → PASS → NOT RUN. `elapsed` = duration (longest first). "
        "`start` = start time. Default: execution order from the output file."
    ),
)
@click.option(
    "--reverse/--no-reverse",
    default=False,
    show_default=True,
    help="Reverse the sort order (only applies with `--sort`).",
)
@pass_application
def show(
    app: Application,
    status_filters: Tuple[str, ...],
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
    output_file: Optional[Path],
    top_n: int,
    message_chars: int,
    full_paths: bool,
    show_tags: bool,
    show_timing: bool,
    sort_field: Optional[str],
    reverse: bool,
) -> None:
    """\
    List individual tests with status, source and failure message.

    One line per test: status badge, full name, `(path:line)` link, and
    the first line of any failure/skip message.

    \b
    Examples:
    ```
    robotcode results show
    robotcode results show --status fail
    robotcode results show --status fail --status skip --tags
    robotcode results show -i smoke -e wipANDnotready
    robotcode results show -s "MyProject.Login.*"
    robotcode results show --top 20
    ```
    """
    profile, root_folder = _resolve_profile(app)
    with app.chdir(root_folder):
        path = _resolve_output_file(app, profile, output_file)
        execution = _load_execution_result(path)

        if include_tags or exclude_tags or suite_globs or test_globs:
            _apply_tree_filters(execution.suite, include_tags, exclude_tags, suite_globs, test_globs)

        wanted = _normalise_statuses(status_filters)
        all_items = [
            _make_test_item(t, message_chars=message_chars, full_paths=full_paths)
            for t in _iter_all_tests(execution.suite)
            if not wanted or t.status in wanted
        ]
        counts = _tally_items(all_items)
        all_items = _sort_items(all_items, sort_field, reverse)
        if top_n > 0:
            shown = all_items[:top_n]
            truncated = max(0, len(all_items) - top_n)
        else:
            shown = all_items
            truncated = 0

        filters_active = bool(status_filters or include_tags or exclude_tags or suite_globs or test_globs)
        data = ShowResult(
            file=_make_file_info(path),
            counts=counts,
            tests=shown,
            truncated=truncated,
            filters_applied=_filters_dict(status_filters, include_tags, exclude_tags, suite_globs, test_globs)
            if filters_active
            else None,
            elapsed_seconds=_elapsed_seconds(execution.suite),
            start_time=_iso(getattr(execution.suite, "start_time", None)),
            end_time=_iso(getattr(execution.suite, "end_time", None)),
        )

        if app.config.output_format in (None, OutputFormat.TEXT):
            app.echo_via_pager(
                _render.render_show(
                    data,
                    show_tags=show_tags,
                    full_paths=full_paths,
                    show_timing=show_timing,
                    sort_field=sort_field,
                    reverse=reverse,
                )
            )
        else:
            app.print_data(data, remove_defaults=True)


@results.command()
@add_options(*RESULT_FILTER_OPTIONS, OUTPUT_OPTION)
@click.option(
    "--level",
    type=click.Choice(["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FAIL"], case_sensitive=False),
    default="INFO",
    show_default=True,
    help="Minimum message level to include.",
)
@click.option(
    "--max-depth",
    "max_depth",
    type=click.IntRange(min=0),
    default=0,
    show_default=True,
    metavar="N",
    help=(
        "Limit nested keyword calls to N levels (0 = unlimited). When a "
        "keyword sits below the limit, its body is collapsed and the "
        "hidden child count is shown instead."
    ),
)
@click.option(
    "--extract",
    "extract_dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help=(
        "Copy/decode referenced artefacts into this directory. Each test's artefacts go into a per-test subdirectory."
    ),
)
@click.option(
    "--full-paths/--no-full-paths",
    default=False,
    show_default=True,
)
@click.option(
    "--timestamps/--no-timestamps",
    "show_timestamps",
    default=False,
    show_default=True,
    help="Show timestamps next to log messages.",
)
@click.option(
    "--timing/--no-timing",
    "show_timing",
    default=True,
    show_default=True,
    help=(
        "Show start time per test/keyword and append start / end / elapsed "
        "of the run as a footer. Use `--no-timing` to suppress."
    ),
)
@click.option(
    "--raw-html/--no-raw-html",
    "raw_html",
    default=False,
    show_default=True,
    help=(
        "Emit HTML messages as raw markup instead of converting them to "
        "plain text. Useful when the HTML is the payload of interest. "
        "Embedded base64 images and external file refs are NOT extracted "
        "in raw mode."
    ),
)
@click.option(
    "--execution-messages/--no-execution-messages",
    "show_execution_messages",
    default=False,
    show_default=True,
    help=("Also show parser/discovery messages from output.xml's `<errors>` section (deduplicated)."),
)
@pass_application
def log(
    app: Application,
    status_filters: Tuple[str, ...],
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
    output_file: Optional[Path],
    level: str,
    max_depth: int,
    extract_dir: Optional[Path],
    full_paths: bool,
    show_timestamps: bool,
    show_timing: bool,
    raw_html: bool,
    show_execution_messages: bool,
) -> None:
    """\
    Show the execution log of each test: keywords, control flow and messages.

    Filter the same way as `show` — by status, tag, suite, or test name.
    Without filters, all tests are included. Use `--max-depth` to collapse
    deeply nested keyword calls.

    \b
    Examples:
    ```
    robotcode results log
    robotcode results log --status fail
    robotcode results log -t "*Login*"
    robotcode results log --level WARN
    robotcode results log --max-depth 2
    robotcode results log -i smoke --extract /tmp/artefacts
    robotcode results log --execution-messages
    ```
    """
    profile, root_folder = _resolve_profile(app)
    with app.chdir(root_folder):
        path = _resolve_output_file(app, profile, output_file)
        execution = _load_execution_result(path)

        if include_tags or exclude_tags or suite_globs or test_globs:
            _apply_tree_filters(execution.suite, include_tags, exclude_tags, suite_globs, test_globs)

        wanted = _normalise_statuses(status_filters)

        base_dir = path.parent
        matched: List[LogTest] = []
        for test in _iter_all_tests(execution.suite):
            if wanted and test.status not in wanted:
                continue
            full_name = _get_full_name(test)
            body, artefacts = _collect_test_body(test, level=level.upper(), base_dir=base_dir, raw_html=raw_html)
            src = getattr(test, "source", None)
            src_str = str(src) if src else None
            matched.append(
                LogTest(
                    full_name=full_name,
                    status=test.status,
                    message=test.message or None,
                    body=body,
                    artifacts=artefacts or None,
                    source=src_str,
                    rel_source=None if full_paths else _rel_to_cwd(src_str),
                    lineno=getattr(test, "lineno", None) or None,
                    elapsed_seconds=_elapsed_seconds(test),
                    start_time=_iso(getattr(test, "start_time", None)),
                )
            )

        exec_messages: Optional[List[LogEntry]] = None
        if show_execution_messages:
            exec_messages = _collect_execution_messages(getattr(execution, "errors", None), raw_html=raw_html) or None

        extracted_count = 0
        extract_abs: Optional[Path] = None
        if extract_dir is not None:
            extract_abs = extract_dir.resolve()
            extract_abs.mkdir(parents=True, exist_ok=True)
            extracted_count = _extract_artifacts(matched, target=extract_abs)

        filters_active = bool(status_filters or include_tags or exclude_tags or suite_globs or test_globs)
        data = LogResult(
            file=_make_file_info(path),
            tests=matched,
            execution_messages=exec_messages,
            extract_dir=str(extract_abs) if extract_abs else None,
            extracted_count=extracted_count,
            elapsed_seconds=_elapsed_seconds(execution.suite),
            start_time=_iso(getattr(execution.suite, "start_time", None)),
            end_time=_iso(getattr(execution.suite, "end_time", None)),
            filters_applied=_filters_dict(status_filters, include_tags, exclude_tags, suite_globs, test_globs)
            if filters_active
            else None,
        )

        if app.config.output_format in (None, OutputFormat.TEXT):
            app.echo_via_pager(
                _render.render_log(
                    data,
                    full_paths=full_paths,
                    level=level,
                    max_depth=max_depth,
                    show_timestamps=show_timestamps,
                    show_timing=show_timing,
                )
            )
        else:
            app.print_data(data, remove_defaults=True)


def _resolve_profile(app: Application) -> Tuple[Any, Optional[Path]]:
    config_files, root_folder, _ = get_config_files(
        None,
        app.config.config_files,
        root_folder=app.config.root,
        no_vcs=app.config.no_vcs,
        verbose_callback=app.verbose,
    )
    try:
        profile = (
            load_robot_config_from_path(*config_files, verbose_callback=app.verbose)
            .combine_profiles(
                *(app.config.profiles or []),
                verbose_callback=app.verbose,
                error_callback=app.error,
            )
            .evaluated_with_env(verbose_callback=app.verbose, error_callback=app.error)
        )
    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e
    return profile, root_folder


def _eval_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return getattr(value, "value", None) or str(value)


def _resolve_output_file(app: Application, profile: Any, explicit: Optional[Path]) -> Path:
    cwd = Path.cwd()
    if explicit is not None:
        target = explicit if explicit.is_absolute() else cwd / explicit
        target = target.resolve()
        if target.is_dir():
            return _auto_discover(app, profile, search_root=target)
        if not target.is_file():
            raise click.UsageError(f"Result file not found: {target}")
        return target

    return _auto_discover(app, profile, search_root=cwd)


def _auto_discover(app: Application, profile: Any, search_root: Path) -> Path:
    raw_output = _eval_str(getattr(profile, "output", None))
    if raw_output is not None and raw_output.upper() == "NONE":
        raise click.UsageError(
            "Profile sets `output = NONE` — no result file to inspect. Pass `--output PATH` explicitly."
        )

    out_dir_raw = _eval_str(getattr(profile, "output_dir", None)) or "."
    out_dir = (search_root / out_dir_raw).resolve() if not Path(out_dir_raw).is_absolute() else Path(out_dir_raw)
    out_name = raw_output or "output.xml"

    candidates = _candidate_paths(search_root=search_root, out_dir=out_dir, out_name=out_name)

    seen: List[Path] = []
    for kind, candidate in candidates:
        if candidate in seen:
            continue
        seen.append(candidate)
        app.verbose(f"trying {kind} candidate: {candidate}")
        if candidate.is_file():
            return candidate
        if kind == "glob":
            matches = sorted(
                (p for p in candidate.parent.glob(candidate.name) if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if matches:
                app.verbose(f"glob matched: {matches[0]}")
                return matches[0]

    raise click.UsageError(
        "No result file found. Searched:\n  " + "\n  ".join(str(p) for p in seen) + "\nPass `--output PATH` explicitly."
    )


def _candidate_paths(*, search_root: Path, out_dir: Path, out_name: str) -> List[Tuple[str, Path]]:
    stem = Path(out_name).stem
    suffix = Path(out_name).suffix or ".xml"

    cands: List[Tuple[str, Path]] = []
    cands.append(("exact", (out_dir / out_name).resolve()))
    # Timestamp-glob in out_dir for the same stem
    cands.append(("glob", (out_dir / f"{stem}-*{suffix}").resolve()))
    # Custom placeholder glob (e.g. output-{timestamp}.xml)
    if "{" in out_name and "}" in out_name:
        cands.append(("glob", (out_dir / re.sub(r"\{[^}]+\}", "*", out_name)).resolve()))
    # JSON peer in same dir
    cands.append(("exact", (out_dir / "output.json").resolve()))
    cands.append(("glob", (out_dir / "output-*.json").resolve()))
    # Legacy fallback in search_root
    if out_dir.resolve() != search_root.resolve():
        cands.append(("exact", (search_root / "output.xml").resolve()))
        cands.append(("exact", (search_root / "output.json").resolve()))
    return cands


def _load_execution_result(path: Path) -> Any:
    if path.suffix.lower() == ".json" and RF_VERSION < (7, 0):
        raise click.ClickException(
            f"Reading JSON result files requires Robot Framework 7.0+; "
            f"got {'.'.join(str(v) for v in RF_VERSION)} (file: {path})."
        )
    try:
        from robot.api import ExecutionResult
    except ImportError as e:
        raise click.ClickException(f"robotframework is not importable: {e}") from e
    try:
        return ExecutionResult(str(path))
    except DataError as e:
        raise click.ClickException(f"failed to parse {path}: {e}") from e
    except Exception as e:
        raise click.ClickException(f"failed to parse {path}: {e}") from e


# Each helper below is bound to one of two implementations at import time —
# the differences between Robot Framework versions are confined to this block.

if RF_VERSION >= (6, 1):

    def _iter_all_tests(suite: Any) -> Iterator[Any]:
        yield from suite.all_tests

else:

    def _iter_all_tests(suite: Any) -> Iterator[Any]:
        yield from suite.tests
        for child in suite.suites:
            yield from _iter_all_tests(child)


if RF_VERSION >= (7, 0):

    def _get_full_name(test: Any) -> str:
        return str(test.full_name or "")

    def _keyword_name_and_owner(item: Any) -> Tuple[Optional[str], str]:
        """Return `(owner, short_name)` for a Keyword/Setup/Teardown body item."""
        return item.owner, str(item.name or "")

    def _loop_variables(item: Any) -> Any:
        """Return the loop variables of a FOR or ITERATION body item."""
        return item.assign

else:

    def _get_full_name(test: Any) -> str:
        return str(test.longname or test.name or "")

    def _keyword_name_and_owner(item: Any) -> Tuple[Optional[str], str]:
        """Return `(owner, short_name)` for a Keyword/Setup/Teardown body item.

        On RF <7 `Keyword.name` already contains the `libname.` prefix; the
        unqualified short name lives in `kwname`.
        """
        return item.libname, str(item.kwname or item.name or "")

    def _loop_variables(item: Any) -> Any:
        """Return the loop variables of a FOR or ITERATION body item.

        RF 7 renamed `For.variables` → `For.assign` (same for ForIteration)."""
        return item.variables


def _elapsed_seconds(item: Any) -> Optional[float]:
    elapsed = getattr(item, "elapsed_time", None)
    if elapsed is None:
        return None
    if hasattr(elapsed, "total_seconds"):
        return float(elapsed.total_seconds())
    try:
        return float(elapsed)
    except (TypeError, ValueError):
        return None


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def _apply_tree_filters(
    suite: Any,
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
) -> None:
    try:
        suite.filter(
            included_suites=list(suite_globs) or None,
            included_tests=list(test_globs) or None,
            included_tags=list(include_tags) or None,
            excluded_tags=list(exclude_tags) or None,
        )
    except DataError as e:
        raise click.ClickException(f"invalid filter pattern: {e}") from e


def _normalise_statuses(statuses: Tuple[str, ...]) -> set[str]:
    return {_STATUS_KEY_MAP.get(s.lower(), s.upper()) for s in statuses}


def _filters_dict(
    status_filters: Tuple[str, ...],
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    if status_filters:
        out["status"] = list(status_filters)
    if include_tags:
        out["include"] = list(include_tags)
    if exclude_tags:
        out["exclude"] = list(exclude_tags)
    if suite_globs:
        out["suite"] = list(suite_globs)
    if test_globs:
        out["test"] = list(test_globs)
    return out


def _bump_counts(c: Counts, status: str) -> None:
    c.total += 1
    if status == "PASS":
        c.passed += 1
    elif status == "FAIL":
        c.failed += 1
    elif status == "SKIP":
        c.skipped += 1
    elif status == "NOT RUN":
        c.not_run += 1


def _collect_counts(suite: Any, status_filters: Tuple[str, ...]) -> Counts:
    wanted = _normalise_statuses(status_filters)
    c = Counts()
    for t in _iter_all_tests(suite):
        if wanted and t.status not in wanted:
            continue
        _bump_counts(c, t.status)
    return c


def _tally_items(items: Iterable[TestResultItem]) -> Counts:
    c = Counts()
    for i in items:
        _bump_counts(c, i.status)
    return c


_STATUS_SORT_RANK = {"FAIL": 0, "SKIP": 1, "PASS": 2, "NOT RUN": 3}


def _sort_items(items: List[TestResultItem], field: Optional[str], reverse: bool) -> List[TestResultItem]:
    if not field:
        return items
    f = field.lower()
    key_map: Dict[str, Callable[[TestResultItem], Any]] = {
        "name": lambda i: (i.full_name or "").lower(),
        "suite": lambda i: (i.suite or "").lower(),
        "status": lambda i: _STATUS_SORT_RANK.get(i.status, 99),
        "elapsed": lambda i: i.elapsed_seconds if i.elapsed_seconds is not None else -1.0,
        "start": lambda i: i.start_time or "",
    }
    # `elapsed` is naturally descending; --reverse flips the meaning either way
    natural_desc = f == "elapsed"
    return sorted(items, key=key_map[f], reverse=natural_desc ^ reverse)


def _rel_to_cwd(p: Optional[str]) -> Optional[str]:
    if p is None:
        return None
    try:
        return str(Path(p).relative_to(Path.cwd()).as_posix())
    except ValueError:
        return None


def _make_file_info(path: Path) -> ResultFileInfo:
    rel = _rel_to_cwd(str(path))
    return ResultFileInfo(
        source=str(path),
        rel_source=rel if rel and rel != str(path) else None,
    )


def _make_test_item(test: Any, *, message_chars: int, full_paths: bool) -> TestResultItem:
    msg = test.message or ""
    first_line = msg.splitlines()[0] if msg else ""
    truncated_msg = first_line
    full_msg: Optional[str] = None
    if message_chars and len(first_line) > message_chars:
        truncated_msg = first_line[:message_chars]
    if msg and (truncated_msg != msg):
        full_msg = msg

    full_name = _get_full_name(test)
    parent_name = _get_full_name(test.parent) if getattr(test, "parent", None) else ""
    src = getattr(test, "source", None)
    src_str = str(src) if src else None
    rel_src = _rel_to_cwd(src_str) if src_str else None
    return TestResultItem(
        name=test.name,
        full_name=full_name,
        suite=parent_name,
        status=test.status,
        message=truncated_msg,
        full_message=full_msg,
        tags=list(test.tags) if getattr(test, "tags", None) else None,
        elapsed_seconds=_elapsed_seconds(test),
        start_time=_iso(getattr(test, "start_time", None)),
        source=src_str,
        rel_source=None if full_paths else rel_src,
        lineno=getattr(test, "lineno", None) or None,
    )


def _collect_failures(suite: Any, status_filters: Tuple[str, ...], *, full_paths: bool = False) -> List[TestResultItem]:
    """Return all failed tests (post-tree-filter, after status filter) with msgs."""
    wanted = _normalise_statuses(status_filters)
    out: List[TestResultItem] = []
    for t in _iter_all_tests(suite):
        if wanted and t.status not in wanted:
            continue
        if t.status != "FAIL":
            continue
        out.append(_make_test_item(t, message_chars=0, full_paths=full_paths))
    return out


def _count_execution_messages(errors: Any) -> Dict[str, int]:
    """Count execution.errors messages grouped by level. Returns empty dict if none."""
    if errors is None:
        return {}
    counts: Dict[str, int] = {}
    for m in getattr(errors, "messages", None) or []:
        level = (getattr(m, "level", "INFO") or "INFO").upper()
        counts[level] = counts.get(level, 0) + 1
    return counts


def _count_all_messages(execution: Any) -> Dict[str, int]:
    """Tally WARN/ERROR/FAIL across parser/discovery AND test runtime messages."""
    counts: Dict[str, int] = {}

    def bump(level: str) -> None:
        if level in ("WARN", "ERROR", "FAIL"):
            counts[level] = counts.get(level, 0) + 1

    for m in getattr(getattr(execution, "errors", None), "messages", None) or []:
        bump((getattr(m, "level", "INFO") or "INFO").upper())

    def walk(items: Iterable[Any]) -> None:
        for item in items:
            t = getattr(item, "type", None)
            if t == "MESSAGE" or (t is None and hasattr(item, "level") and hasattr(item, "message")):
                bump((getattr(item, "level", "INFO") or "INFO").upper())
                continue
            body = getattr(item, "body", None)
            if body is not None:
                walk(body)
            if getattr(item, "has_setup", False):
                walk([item.setup])
            if getattr(item, "has_teardown", False):
                walk([item.teardown])

    for test in _iter_all_tests(execution.suite):
        if getattr(test, "has_setup", False):
            walk([test.setup])
        walk(getattr(test, "body", []) or [])
        if getattr(test, "has_teardown", False):
            walk([test.teardown])

    return counts


def _collect_execution_messages(errors: Any, *, raw_html: bool = False) -> List[LogEntry]:
    """Collect parser/discovery messages from `output.xml`'s <errors> section
    as LogEntry items, preserving order and individual timestamps."""
    if errors is None:
        return []
    out: List[LogEntry] = []
    for m in getattr(errors, "messages", None) or []:
        level = (getattr(m, "level", "INFO") or "INFO").upper()
        text = getattr(m, "message", "") or ""
        is_html = bool(getattr(m, "html", False))
        ts = _iso(getattr(m, "timestamp", None))
        if is_html and not raw_html:
            text = _html.html_to_markdown(text, base_dir=Path("."), on_artifact=lambda _r: None)
        out.append(LogEntry(type="MESSAGE", level=level, timestamp=ts, text=text, is_html=is_html))
    return out


_LEVEL_ORDER = {"TRACE": 0, "DEBUG": 1, "INFO": 2, "WARN": 3, "ERROR": 4, "FAIL": 5}
_KEYWORD_TYPES = {"KEYWORD", "SETUP", "TEARDOWN"}


def _collect_test_body(
    test: Any, *, level: str, base_dir: Path, raw_html: bool = False
) -> Tuple[List[LogEntry], List[ArtifactRef]]:
    threshold = _LEVEL_ORDER.get(level, 2)
    test_artefacts: List[ArtifactRef] = []

    def collect(ref: ArtifactRef) -> None:
        test_artefacts.append(ref)

    def build(item: Any) -> Optional[LogEntry]:
        t = getattr(item, "type", "") or ""

        if t == "MESSAGE" or (not t and hasattr(item, "level") and hasattr(item, "message")):
            lvl = (getattr(item, "level", "INFO") or "INFO").upper()
            if _LEVEL_ORDER.get(lvl, 2) < threshold:
                return None
            return _make_message_entry(item, base_dir, collect, raw_html=raw_html)

        children: List[LogEntry] = []
        if getattr(item, "has_setup", False):
            e = build(item.setup)
            if e is not None:
                children.append(e)
        for child in getattr(item, "body", None) or []:
            e = build(child)
            if e is not None:
                children.append(e)
        if getattr(item, "has_teardown", False):
            e = build(item.teardown)
            if e is not None:
                children.append(e)

        common: Dict[str, Any] = {
            "status": getattr(item, "status", None),
            "message": getattr(item, "message", None) or None,
            "elapsed_seconds": _elapsed_seconds(item),
            "start_time": _iso(getattr(item, "start_time", None)),
            "body": children or None,
        }

        if t in _KEYWORD_TYPES:
            owner, short = _keyword_name_and_owner(item)
            full_name = f"{owner}.{short}" if owner and short else short
            return LogEntry(
                type=t,
                name=full_name or None,
                args=list(item.args or []) or None,
                assign=list(item.assign or []) or None,
                **common,
            )

        if t == "FOR":
            return LogEntry(
                type="FOR",
                assign=list(_loop_variables(item) or []) or None,
                flavor=item.flavor or None,
                args=list(item.values or []) or None,
                **common,
            )

        if t == "ITERATION":
            return LogEntry(
                type="ITERATION",
                assign=list(_loop_variables(item) or []) or None,
                **common,
            )

        if t == "WHILE":
            return LogEntry(
                type="WHILE",
                condition=getattr(item, "condition", None) or None,
                **common,
            )

        if t in ("IF/ELSE ROOT", "TRY/EXCEPT ROOT"):
            label = "IF" if t == "IF/ELSE ROOT" else "TRY"
            common["status"] = None
            common["message"] = None
            common["elapsed_seconds"] = None
            common["start_time"] = None
            return LogEntry(type=label, **common)

        if t in ("IF", "ELSE IF", "ELSE"):
            return LogEntry(
                type=t,
                condition=getattr(item, "condition", None) or None,
                **common,
            )

        if t in ("EXCEPT", "FINALLY"):
            return LogEntry(
                type=t,
                patterns=list(getattr(item, "patterns", []) or []) or None,
                pattern_type=getattr(item, "pattern_type", None) or None,
                assign=([getattr(item, "assign")] if getattr(item, "assign", None) else None),
                **common,
            )

        if t == "VAR":
            return LogEntry(
                type="VAR",
                assign=[getattr(item, "name", "")] if getattr(item, "name", None) else None,
                args=list(getattr(item, "value", []) or []) or None,
                scope=getattr(item, "scope", None) or None,
                separator=getattr(item, "separator", None) or None,
                **common,
            )

        if t == "RETURN":
            return LogEntry(
                type="RETURN",
                args=list(getattr(item, "values", []) or []) or None,
                **common,
            )

        if t in ("CONTINUE", "BREAK"):
            return LogEntry(type=t, **common)

        if t == "GROUP":
            return LogEntry(type="GROUP", name=getattr(item, "name", None) or None, **common)

        if t == "ERROR":
            return LogEntry(
                type="ERROR",
                args=list(getattr(item, "values", []) or []) or None,
                **common,
            )

        return LogEntry(type=t or "UNKNOWN", **common)

    out: List[LogEntry] = []
    if getattr(test, "has_setup", False):
        e = build(test.setup)
        if e is not None:
            out.append(e)
    for child in getattr(test, "body", None) or []:
        e = build(child)
        if e is not None:
            out.append(e)
    if getattr(test, "has_teardown", False):
        e = build(test.teardown)
        if e is not None:
            out.append(e)

    return out, _html.dedup_artefacts(test_artefacts)


def _make_message_entry(
    msg: Any,
    base_dir: Path,
    on_artifact: Callable[[ArtifactRef], None],
    *,
    raw_html: bool = False,
) -> LogEntry:
    is_html = bool(getattr(msg, "html", False))
    raw = getattr(msg, "message", "") or ""
    msg_artefacts: List[ArtifactRef] = []

    def collect(ref: ArtifactRef) -> None:
        msg_artefacts.append(ref)
        on_artifact(ref)

    if is_html and not raw_html:
        text = _html.html_to_markdown(raw, base_dir=base_dir, on_artifact=collect)
    else:
        text = raw

    msg_artefacts = _html.dedup_artefacts(msg_artefacts)
    return LogEntry(
        type="MESSAGE",
        level=(getattr(msg, "level", "INFO") or "INFO").upper(),
        timestamp=_iso(getattr(msg, "timestamp", None)),
        text=text,
        is_html=is_html,
        artifacts=msg_artefacts or None,
    )


def _slugify(s: str) -> str:
    slug = re.sub(r"[^\w.-]+", "_", s).strip("_")[:200]
    return slug or "_test"


def _extract_artifacts(tests: List[LogTest], *, target: Path) -> int:
    target = target.resolve()
    count = 0
    for t in tests:
        if not t.artifacts:
            continue
        slug = _slugify(t.full_name)
        test_dir = (target / slug).resolve()
        try:
            test_dir.relative_to(target)
        except ValueError:
            for ref in t.artifacts:
                ref.skipped_reason = ref.skipped_reason or "target-traversal"
            continue
        test_dir.mkdir(parents=True, exist_ok=True)

        seq_embedded = 0
        used_names: Dict[str, int] = {}
        for ref in t.artifacts:
            if ref.skipped_reason:
                continue
            if ref.embedded:
                data = _html.get_embedded_data(ref)
                if data is None:
                    ref.skipped_reason = "no-data"
                    continue
                ext = _html.ext_from_media_type(ref.media_type)
                fname = _unique_name(f"embedded-{seq_embedded}{ext}", used_names)
                seq_embedded += 1
                dest = (test_dir / fname).resolve()
                try:
                    dest.relative_to(test_dir)
                except ValueError:
                    ref.skipped_reason = "target-traversal"
                    continue
                dest.write_bytes(data)
                ref.extracted_to = str(dest)
                count += 1
            elif ref.resolved_path:
                src_path = Path(ref.resolved_path)
                if not src_path.is_file():
                    ref.skipped_reason = "missing-source"
                    continue
                fname = _unique_name(src_path.name, used_names)
                dest = (test_dir / fname).resolve()
                try:
                    dest.relative_to(test_dir)
                except ValueError:
                    ref.skipped_reason = "target-traversal"
                    continue
                shutil.copy2(src_path, dest)
                ref.extracted_to = str(dest)
                count += 1
    return count


def _unique_name(name: str, used: Dict[str, int]) -> str:
    if name not in used:
        used[name] = 1
        return name
    seq = used[name]
    used[name] = seq + 1
    stem, dot, ext = name.rpartition(".")
    if dot:
        return f"{stem}-{seq}.{ext}"
    return f"{name}-{seq}"
