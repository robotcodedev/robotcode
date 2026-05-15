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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

import click
from robot.errors import DataError
from robot.result import ForIteration
from robot.utils import normalize

from robotcode.modifiers import ByLongName, ExcludedByLongName
from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.utils import get_config_files
from robotcode.robot.utils import RF_VERSION

from . import _html, _render
from ._models import (
    ArtifactRef,
    Counts,
    DiffChange,
    DiffResult,
    LogEntry,
    LogResult,
    LogTest,
    ResultFileInfo,
    ShowResult,
    StatsGroup,
    StatsResult,
    StatsSection,
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
        help="Only include tests with one of these statuses.",
    ),
    click.option(
        "-i",
        "--include",
        "include_tags",
        multiple=True,
        metavar="TAG_PATTERN",
        help=("Include tests matching the tag pattern. Supports Robot's tag pattern syntax (AND, OR, NOT, *, ?)."),
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
    click.option(
        "-bl",
        "--by-longname",
        "by_longname",
        multiple=True,
        metavar="NAME",
        help="Select tests/tasks or suites by long name (exact match).",
    ),
    click.option(
        "-ebl",
        "--exclude-by-longname",
        "exclude_by_longname",
        multiple=True,
        metavar="NAME",
        help="Exclude tests/tasks or suites by long name (exact match).",
    ),
]


SEARCH_OPTIONS = [
    click.option(
        "--search",
        "search_substring",
        metavar="TEXT",
        default=None,
        help=(
            "Only include tests with at least one case-insensitive substring "
            "match against TEXT. Searches test name, full name, failure "
            "message, tags, keyword names, keyword arguments, and log "
            "messages. Mutually exclusive with `--search-regex`."
        ),
    ),
    click.option(
        "--search-regex",
        "search_regex",
        metavar="PATTERN",
        default=None,
        help=(
            "Only include tests with at least one match against PATTERN "
            "(Python regular expression, case-sensitive — prefix with `(?i)` "
            "for case-insensitive). Same target fields as `--search`. "
            "Mutually exclusive with `--search`."
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
@add_options(*RESULT_FILTER_OPTIONS, *SEARCH_OPTIONS, OUTPUT_OPTION)
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
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    search_substring: Optional[str],
    search_regex: Optional[str],
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
    robotcode results summary --search TimeoutError
    robotcode --format json results summary
    ```
    """
    profile, root_folder = _resolve_profile(app)
    with app.chdir(root_folder):
        path = _resolve_output_file(app, profile, output_file)
        execution = _load_execution_result(path)

        filters_active = bool(
            status_filters
            or include_tags
            or exclude_tags
            or suite_globs
            or test_globs
            or by_longname
            or exclude_by_longname
            or search_substring
            or search_regex
        )
        if include_tags or exclude_tags or suite_globs or test_globs or by_longname or exclude_by_longname:
            _apply_tree_filters(
                execution.suite,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
            )
        match = _make_matcher(search_substring, search_regex)
        counts = _collect_counts(execution.suite, status_filters, match)
        failures = (
            _collect_failures(execution.suite, status_filters, full_paths=full_paths, match=match)
            if show_failures
            else None
        )
        exec_msg_counts = _count_execution_messages(getattr(execution, "errors", None))
        msg_counts = _count_all_messages(execution)

        data = SummaryResult(
            file=_make_file_info(path),
            status=execution.suite.status,
            counts=counts,
            elapsed_seconds=_elapsed_seconds(execution.suite),
            start_time=_iso(_start_time(execution.suite)),
            end_time=_iso(_end_time(execution.suite)),
            failures=failures or None,
            messages_count=msg_counts or None,
            execution_messages_count=exec_msg_counts or None,
            filters_applied=_filters_dict(
                status_filters,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
                search_substring,
                search_regex,
            )
            if filters_active
            else None,
        )

        if app.config.output_format in (None, OutputFormat.TEXT):
            app.echo_via_pager(_render.render_summary(data, full_paths=full_paths))
        else:
            app.print_data(data, remove_defaults=True)


@results.command()
@add_options(*RESULT_FILTER_OPTIONS, *SEARCH_OPTIONS, OUTPUT_OPTION)
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
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    search_substring: Optional[str],
    search_regex: Optional[str],
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
    robotcode results show --search "AssertionError"
    ```
    """
    profile, root_folder = _resolve_profile(app)
    with app.chdir(root_folder):
        path = _resolve_output_file(app, profile, output_file)
        execution = _load_execution_result(path)

        if include_tags or exclude_tags or suite_globs or test_globs or by_longname or exclude_by_longname:
            _apply_tree_filters(
                execution.suite,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
            )

        wanted = _normalise_statuses(status_filters)
        match = _make_matcher(search_substring, search_regex)
        all_items = [
            _make_test_item(t, message_chars=message_chars, full_paths=full_paths)
            for t in _iter_all_tests(execution.suite)
            if (not wanted or t.status in wanted) and (match is None or _raw_test_search_matches(t, match))
        ]
        counts = _tally_items(all_items)
        all_items = _sort_items(all_items, sort_field, reverse)
        if top_n > 0:
            shown = all_items[:top_n]
            truncated = max(0, len(all_items) - top_n)
        else:
            shown = all_items
            truncated = 0

        filters_active = bool(
            status_filters
            or include_tags
            or exclude_tags
            or suite_globs
            or test_globs
            or by_longname
            or exclude_by_longname
            or search_substring
            or search_regex
        )
        data = ShowResult(
            file=_make_file_info(path),
            counts=counts,
            tests=shown,
            truncated=truncated,
            filters_applied=_filters_dict(
                status_filters,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
                search_substring,
                search_regex,
            )
            if filters_active
            else None,
            elapsed_seconds=_elapsed_seconds(execution.suite),
            start_time=_iso(_start_time(execution.suite)),
            end_time=_iso(_end_time(execution.suite)),
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
                    search_substring=search_substring,
                    search_regex=search_regex,
                )
            )
        else:
            app.print_data(data, remove_defaults=True)


@results.command()
@add_options(*RESULT_FILTER_OPTIONS, *SEARCH_OPTIONS, OUTPUT_OPTION)
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
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    search_substring: Optional[str],
    search_regex: Optional[str],
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
    robotcode results log --search "TimeoutError"
    robotcode results log --execution-messages
    ```
    """
    profile, root_folder = _resolve_profile(app)
    with app.chdir(root_folder):
        path = _resolve_output_file(app, profile, output_file)
        execution = _load_execution_result(path)

        if include_tags or exclude_tags or suite_globs or test_globs or by_longname or exclude_by_longname:
            _apply_tree_filters(
                execution.suite,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
            )

        wanted = _normalise_statuses(status_filters)
        match = _make_matcher(search_substring, search_regex)

        base_dir = path.parent
        matched: List[LogTest] = []
        for test in _iter_all_tests(execution.suite):
            if wanted and test.status not in wanted:
                continue
            if match is not None and not _raw_test_search_matches(test, match):
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
                    start_time=_iso(_start_time(test)),
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

        filters_active = bool(
            status_filters
            or include_tags
            or exclude_tags
            or suite_globs
            or test_globs
            or by_longname
            or exclude_by_longname
            or search_substring
            or search_regex
        )
        data = LogResult(
            file=_make_file_info(path),
            tests=matched,
            execution_messages=exec_messages,
            extract_dir=str(extract_abs) if extract_abs else None,
            extracted_count=extracted_count,
            elapsed_seconds=_elapsed_seconds(execution.suite),
            start_time=_iso(_start_time(execution.suite)),
            end_time=_iso(_end_time(execution.suite)),
            filters_applied=_filters_dict(
                status_filters,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
                search_substring,
                search_regex,
            )
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
                    search_substring=search_substring,
                    search_regex=search_regex,
                    show_timestamps=show_timestamps,
                    show_timing=show_timing,
                )
            )
        else:
            app.print_data(data, remove_defaults=True)


@results.command()
@add_options(*RESULT_FILTER_OPTIONS, *SEARCH_OPTIONS, OUTPUT_OPTION)
@click.option(
    "--by",
    "group_by",
    type=click.Choice(["tag", "suite", "status"], case_sensitive=False),
    multiple=True,
    default=("status",),
    show_default=True,
    help="Group tests by this attribute (one section per value).",
)
@click.option(
    "--sort",
    "group_sort",
    type=click.Choice(["name", "total", "failed", "elapsed"], case_sensitive=False),
    default="failed",
    show_default=True,
    help="Within each section: sort groups by this metric (descending).",
)
@click.option(
    "--top",
    "top_n",
    type=click.IntRange(min=0),
    default=0,
    show_default=True,
    help="Show at most N groups per section (0 = all).",
)
@pass_application
def stats(
    app: Application,
    status_filters: Tuple[str, ...],
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    search_substring: Optional[str],
    search_regex: Optional[str],
    output_file: Optional[Path],
    group_by: Tuple[str, ...],
    group_sort: str,
    top_n: int,
) -> None:
    """\
    Aggregate results by tag, suite, or status.

    Each section is a table with pass/fail/skip counts and total elapsed
    per group. Repeat `--by` to render multiple sections in one go.

    \b
    Examples:
    ```
    robotcode results stats
    robotcode results stats --by tag
    robotcode results stats --by tag --by suite
    robotcode results stats --by tag --sort elapsed --top 20
    robotcode results stats --by tag --search Browser
    robotcode --format json results stats --by tag
    ```
    """
    profile, root_folder = _resolve_profile(app)
    with app.chdir(root_folder):
        path = _resolve_output_file(app, profile, output_file)
        execution = _load_execution_result(path)

        if include_tags or exclude_tags or suite_globs or test_globs or by_longname or exclude_by_longname:
            _apply_tree_filters(
                execution.suite,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
            )

        wanted = _normalise_statuses(status_filters)
        match = _make_matcher(search_substring, search_regex)
        tests = [
            t
            for t in _iter_all_tests(execution.suite)
            if (not wanted or t.status in wanted) and (match is None or _raw_test_search_matches(t, match))
        ]

        seen_dimensions: List[str] = []
        for dim in group_by:
            d = dim.lower()
            if d not in seen_dimensions:
                seen_dimensions.append(d)

        sections = [_build_stats_section(d, tests, group_sort.lower(), top_n) for d in seen_dimensions]

        filters_active = bool(
            status_filters
            or include_tags
            or exclude_tags
            or suite_globs
            or test_globs
            or by_longname
            or exclude_by_longname
            or search_substring
            or search_regex
        )
        data = StatsResult(
            file=_make_file_info(path),
            sections=sections,
            filters_applied=_filters_dict(
                status_filters,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
                search_substring,
                search_regex,
            )
            if filters_active
            else None,
        )

        if app.config.output_format in (None, OutputFormat.TEXT):
            app.echo_via_pager(_render.render_stats(data))
        else:
            app.print_data(data, remove_defaults=True)


def _build_stats_section(dimension: str, tests: List[Any], group_sort: str, top_n: int) -> StatsSection:
    buckets: Dict[str, Counts] = {}
    elapsed: Dict[str, float] = {}

    def _bump(name: str, status: str, secs: Optional[float]) -> None:
        c = buckets.setdefault(name, Counts())
        _bump_counts(c, status)
        if secs is not None:
            elapsed[name] = elapsed.get(name, 0.0) + secs

    for t in tests:
        secs = _elapsed_seconds(t)
        if dimension == "status":
            _bump(t.status, t.status, secs)
        elif dimension == "suite":
            suite = getattr(t, "parent", None)
            suite_name = _get_full_name(suite) if suite is not None else ""
            _bump(suite_name or "(root)", t.status, secs)
        elif dimension == "tag":
            tags = list(getattr(t, "tags", None) or [])
            if not tags:
                continue
            # Robot Framework treats tags as equal when they only differ in
            # case, whitespace or underscores (`Bug 1` ≡ `bug_1` ≡ `bug1`).
            # We bucket *and* display by the normalized form so semantically-
            # equal tags both merge into one group and surface that fact.
            for tag in tags:
                _bump(normalize(str(tag), ignore="_"), t.status, secs)

    groups = [
        StatsGroup(name=name, counts=counts, elapsed_seconds=elapsed.get(name) or None)
        for name, counts in buckets.items()
    ]

    group_key_map: Dict[str, Tuple[Callable[[StatsGroup], Any], bool]] = {
        "name": (lambda g: g.name.lower(), False),
        "total": (lambda g: g.counts.total, True),
        "elapsed": (lambda g: g.elapsed_seconds or 0.0, True),
        "failed": (lambda g: g.counts.failed, True),
    }
    sort_key, reverse = group_key_map.get(group_sort, group_key_map["failed"])
    groups.sort(key=sort_key, reverse=reverse)

    truncated = 0
    if top_n > 0 and len(groups) > top_n:
        truncated = len(groups) - top_n
        groups = groups[:top_n]

    return StatsSection(dimension=dimension, groups=groups, truncated=truncated)


_DIFF_CATEGORIES = ("new-failures", "new-passes", "status-changes", "added", "removed")


@results.command()
@click.argument(
    "baseline",
    type=click.Path(path_type=Path, exists=True, dir_okay=False, readable=True),
)
@click.argument(
    "current",
    type=click.Path(path_type=Path, exists=True, dir_okay=False, readable=True),
    required=False,
)
@add_options(*RESULT_FILTER_OPTIONS, *SEARCH_OPTIONS)
@click.option(
    "--full-paths/--no-full-paths",
    default=False,
    show_default=True,
    help="Show absolute source paths instead of paths relative to cwd.",
)
@click.option(
    "--message-chars",
    type=click.IntRange(min=0),
    default=120,
    show_default=True,
    help="Truncate failure messages to N characters (0 = no truncation).",
)
@click.option(
    "--only",
    "only_categories",
    type=click.Choice(_DIFF_CATEGORIES, case_sensitive=False),
    multiple=True,
    default=(),
    help="Restrict output to these categories. Default: all.",
)
@pass_application
def diff(
    app: Application,
    baseline: Path,
    current: Optional[Path],
    status_filters: Tuple[str, ...],
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    search_substring: Optional[str],
    search_regex: Optional[str],
    full_paths: bool,
    message_chars: int,
    only_categories: Tuple[str, ...],
) -> None:
    """\
    Compare two output files: status changes plus added/removed tests.

    If `CURRENT` is omitted, it is auto-discovered from the active profile
    so you can diff a saved baseline against the latest run.

    \b
    Examples:
    ```
    robotcode results diff baseline.xml
    robotcode results diff prev/output.xml curr/output.xml
    robotcode results diff baseline.xml --only new-failures
    robotcode results diff baseline.xml -i smoke
    robotcode results diff baseline.xml --search TimeoutError
    robotcode --format json results diff baseline.xml
    ```
    """
    profile, root_folder = _resolve_profile(app)
    with app.chdir(root_folder):
        baseline_path = baseline.resolve()
        if current is not None:
            current_path = current.resolve()
        else:
            current_path = _resolve_output_file(app, profile, None)

        baseline_exec = _load_execution_result(baseline_path)
        current_exec = _load_execution_result(current_path)

        tree_filter = any([include_tags, exclude_tags, suite_globs, test_globs, by_longname, exclude_by_longname])
        if tree_filter:
            _apply_tree_filters(
                baseline_exec.suite,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
            )
            _apply_tree_filters(
                current_exec.suite,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
            )

        wanted = _normalise_statuses(status_filters)
        match = _make_matcher(search_substring, search_regex)

        def _eligible(t: Any) -> bool:
            if wanted and t.status not in wanted:
                return False
            if match is not None and not _raw_test_search_matches(t, match):
                return False
            return True

        baseline_tests = {_get_full_name(t): t for t in _iter_all_tests(baseline_exec.suite) if _eligible(t)}
        current_tests = {_get_full_name(t): t for t in _iter_all_tests(current_exec.suite) if _eligible(t)}

        new_failures: List[DiffChange] = []
        new_passes: List[DiffChange] = []
        status_changes: List[DiffChange] = []
        added: List[DiffChange] = []
        removed: List[DiffChange] = []

        for name, cur in current_tests.items():
            base = baseline_tests.get(name)
            if base is None:
                added.append(_make_diff_change(name, None, cur, message_chars=message_chars, full_paths=full_paths))
                continue
            if base.status == cur.status:
                continue
            change = _make_diff_change(name, base, cur, message_chars=message_chars, full_paths=full_paths)
            if base.status == "PASS" and cur.status in ("FAIL", "ERROR"):
                new_failures.append(change)
            elif base.status in ("FAIL", "ERROR", "SKIP") and cur.status == "PASS":
                new_passes.append(change)
            else:
                status_changes.append(change)

        for name, base in baseline_tests.items():
            if name not in current_tests:
                removed.append(_make_diff_change(name, base, None, message_chars=message_chars, full_paths=full_paths))

        selected = {c.lower() for c in only_categories} if only_categories else None

        filters_active = bool(
            status_filters
            or include_tags
            or exclude_tags
            or suite_globs
            or test_globs
            or by_longname
            or exclude_by_longname
            or search_substring
            or search_regex
        )
        data = DiffResult(
            baseline=_make_file_info(baseline_path),
            current=_make_file_info(current_path),
            new_failures=new_failures if selected is None or "new-failures" in selected else None,
            new_passes=new_passes if selected is None or "new-passes" in selected else None,
            status_changes=status_changes if selected is None or "status-changes" in selected else None,
            added=added if selected is None or "added" in selected else None,
            removed=removed if selected is None or "removed" in selected else None,
            filters_applied=_filters_dict(
                status_filters,
                include_tags,
                exclude_tags,
                suite_globs,
                test_globs,
                by_longname,
                exclude_by_longname,
                search_substring,
                search_regex,
            )
            if filters_active
            else None,
        )

        if app.config.output_format in (None, OutputFormat.TEXT):
            app.echo_via_pager(_render.render_diff(data, full_paths=full_paths))
        else:
            app.print_data(data, remove_defaults=True)


def _make_diff_change(
    full_name: str,
    baseline_test: Any,
    current_test: Any,
    *,
    message_chars: int,
    full_paths: bool,
) -> DiffChange:
    """Build a DiffChange capturing baseline/current status, message, and source."""
    src_test = current_test if current_test is not None else baseline_test
    src = getattr(src_test, "source", None)
    src_str = str(src) if src else None
    return DiffChange(
        full_name=full_name,
        baseline_status=baseline_test.status if baseline_test is not None else None,
        current_status=current_test.status if current_test is not None else None,
        baseline_message=_truncate(getattr(baseline_test, "message", None), message_chars)
        if baseline_test is not None
        else None,
        current_message=_truncate(getattr(current_test, "message", None), message_chars)
        if current_test is not None
        else None,
        source=src_str,
        rel_source=None if full_paths else _rel_to_cwd(src_str),
        lineno=getattr(src_test, "lineno", None) or None,
    )


def _truncate(text: Optional[str], limit: int) -> Optional[str]:
    if not text:
        return None
    first_line = text.splitlines()[0]
    if limit and len(first_line) > limit:
        return first_line[:limit].rstrip() + "…"
    return first_line


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
        """Loop variables for a `For` or `ForIteration` body item (RF 7+ name)."""
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
        """Loop variables for a `For` or `ForIteration` body item (RF <7 name)."""
        return item.variables


def _elapsed_seconds(item: Any) -> Optional[float]:
    elapsed = getattr(item, "elapsed_time", None)
    if elapsed is not None:
        if hasattr(elapsed, "total_seconds"):
            return float(elapsed.total_seconds())
        try:
            return float(elapsed)
        except (TypeError, ValueError):
            return None
    legacy = getattr(item, "elapsedtime", None)
    if legacy is not None:
        try:
            return float(legacy) / 1000.0
        except (TypeError, ValueError):
            return None
    return None


def _start_time(item: Any) -> Any:
    """Read a body-item's start time, accepting RF 7+ `start_time` and RF <7 `starttime`."""
    return getattr(item, "start_time", None) or getattr(item, "starttime", None)


def _end_time(item: Any) -> Any:
    """Read a body-item's end time, accepting RF 7+ `end_time` and RF <7 `endtime`."""
    return getattr(item, "end_time", None) or getattr(item, "endtime", None)


_LEGACY_TS_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})\s+(\d{2}:\d{2}:\d{2}(?:\.\d+)?)$")


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    text = str(value)
    m = _LEGACY_TS_RE.match(text)
    if m:
        y, mo, d, time_part = m.groups()
        return f"{y}-{mo}-{d}T{time_part}"
    return text


def _apply_tree_filters(
    suite: Any,
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
    by_longname: Tuple[str, ...] = (),
    exclude_by_longname: Tuple[str, ...] = (),
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
    if by_longname:
        suite.visit(ByLongName(*by_longname))
    if exclude_by_longname:
        suite.visit(ExcludedByLongName(*exclude_by_longname))


def _normalise_statuses(statuses: Tuple[str, ...]) -> set[str]:
    return {_STATUS_KEY_MAP.get(s.lower(), s.upper()) for s in statuses}


# Robot Framework treats any uppercase `AND` / `OR` / `NOT` substring inside
# a tag pattern as a logical operator — even without surrounding whitespace,
# and even when embedded in a longer word (so `MEMORY` parses as `mem OR y`).
# We mirror that detection so we don't accidentally lower-case an operator.
_TAG_PATTERN_OPERATOR_RE = re.compile(r"AND|OR|NOT")


def _canonical_tag_pattern(pattern: str) -> str:
    """Echo a tag pattern in its canonical form.

    For plain single tags this normalises the way Robot does for tag
    matching: lowercase, no whitespace, no underscores (so `Bug 1` becomes
    `bug1`). For patterns Robot parses as a logical expression (containing
    an uppercase `AND` / `OR` / `NOT`) we echo the input verbatim, since
    each operand would need to be normalised individually and the structure
    carries meaning the user typed deliberately.
    """
    if _TAG_PATTERN_OPERATOR_RE.search(pattern):
        return pattern
    return str(normalize(pattern, ignore="_"))


def _filters_dict(
    status_filters: Tuple[str, ...],
    include_tags: Tuple[str, ...],
    exclude_tags: Tuple[str, ...],
    suite_globs: Tuple[str, ...],
    test_globs: Tuple[str, ...],
    by_longname: Tuple[str, ...] = (),
    exclude_by_longname: Tuple[str, ...] = (),
    search_substring: Optional[str] = None,
    search_regex: Optional[str] = None,
) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    if status_filters:
        out["status"] = list(status_filters)
    if include_tags:
        out["include"] = [_canonical_tag_pattern(p) for p in include_tags]
    if exclude_tags:
        out["exclude"] = [_canonical_tag_pattern(p) for p in exclude_tags]
    if suite_globs:
        out["suite"] = list(suite_globs)
    if test_globs:
        out["test"] = list(test_globs)
    if by_longname:
        out["by-longname"] = list(by_longname)
    if exclude_by_longname:
        out["exclude-by-longname"] = list(exclude_by_longname)
    if search_substring:
        out["search"] = [search_substring]
    if search_regex:
        out["search-regex"] = [search_regex]
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


def _collect_counts(
    suite: Any,
    status_filters: Tuple[str, ...],
    match: Optional["_SearchMatcher"] = None,
) -> Counts:
    wanted = _normalise_statuses(status_filters)
    c = Counts()
    for t in _iter_all_tests(suite):
        if wanted and t.status not in wanted:
            continue
        if match is not None and not _raw_test_search_matches(t, match):
            continue
        _bump_counts(c, t.status)
    return c


def _tally_items(items: Iterable[TestResultItem]) -> Counts:
    c = Counts()
    for i in items:
        _bump_counts(c, i.status)
    return c


_STATUS_SORT_RANK = {"FAIL": 0, "SKIP": 1, "PASS": 2, "NOT RUN": 3}


@dataclass(frozen=True)
class _SearchMatcher:
    """A pair of predicates: one for general targets, one for tags.

    `tag` applies Robot's tag-normalization (lowercase, no whitespace, no
    underscores) on both sides before comparing, so a search for `bug 123`
    matches tests tagged `bug_123` and vice versa. `general` is the plain
    substring or regex predicate used for everything else (names, messages,
    keyword arguments, …).
    """

    general: Callable[[Optional[str]], bool]
    tag: Callable[[Optional[str]], bool]


def _make_matcher(substring: Optional[str], regex: Optional[str]) -> Optional[_SearchMatcher]:
    """Compile a search predicate once.

    Exactly one of `substring` / `regex` may be set. `substring` is matched
    case-insensitively as a plain `in` check. `regex` is matched without any
    case-folding by default — use `(?i)pattern` to make a regex
    case-insensitive. Returns `None` if neither is given.
    """
    if substring and regex:
        raise click.UsageError("--search and --search-regex are mutually exclusive.")
    if substring:
        needle = substring.lower()
        needle_norm = normalize(substring, ignore="_")

        def general(s: Optional[str]) -> bool:
            return bool(s and needle in s.lower())

        def tag(s: Optional[str]) -> bool:
            return bool(s and needle_norm in normalize(s, ignore="_"))

        return _SearchMatcher(general=general, tag=tag)
    if regex:
        try:
            rx = re.compile(regex)
        except re.error as e:
            raise click.UsageError(f"--search-regex: invalid pattern: {e}") from e

        def general(s: Optional[str]) -> bool:
            return bool(s and rx.search(s))

        def tag(s: Optional[str]) -> bool:
            return bool(s and rx.search(normalize(s, ignore="_")))

        return _SearchMatcher(general=general, tag=tag)
    return None


def _raw_test_search_matches(test: Any, matcher: _SearchMatcher) -> bool:
    """True if the raw Robot test (or anything in its body tree) matches.

    Walks the raw `output.xml` model so callers don't have to materialise the
    body as LogEntry objects first. Tags are matched in their normalised form
    so `bug 123`, `bug_123`, and `Bug123` are treated as the same tag.
    """
    if (
        matcher.general(_get_full_name(test))
        or matcher.general(getattr(test, "message", None))
        or any(matcher.tag(str(t)) for t in (getattr(test, "tags", None) or []))
    ):
        return True
    return _raw_body_matches(getattr(test, "body", None), matcher.general)


def _raw_body_matches(body: Any, match: Callable[[Optional[str]], bool]) -> bool:
    """Recurse through a raw body iterable looking for any match.

    Inspects body-item attributes per type (mirrors `_collect_test_body`'s
    dispatch), so we never read attributes that Robot has deprecated for a
    given item type (e.g. `name`/`args` on `If`/`Try` body items).
    """
    if not body:
        return False
    for item in body:
        t = getattr(item, "type", "") or ""

        if t == "MESSAGE" or (not t and hasattr(item, "level") and hasattr(item, "message")):
            if match(getattr(item, "message", None)):
                return True
            continue

        if match(getattr(item, "message", None)):
            return True

        if t in _KEYWORD_TYPES:
            owner, short = _keyword_name_and_owner(item)
            full_name = f"{owner}.{short}" if owner and short else short
            if match(full_name):
                return True
            if any(match(a) for a in (item.args or [])):
                return True
            if any(match(a) for a in (item.assign or [])):
                return True
        elif t == "FOR":
            if any(match(v) for v in (_loop_variables(item) or [])):
                return True
            if any(match(v) for v in (item.values or [])):
                return True
            if match(item.flavor):
                return True
        elif t in ("WHILE", "IF", "ELSE IF"):
            if match(getattr(item, "condition", None)):
                return True
        elif t == "VAR":
            if match(getattr(item, "name", None)):
                return True
            if any(match(v) for v in (getattr(item, "value", None) or [])):
                return True
        elif t == "RETURN":
            if any(match(v) for v in (getattr(item, "values", None) or [])):
                return True
        elif t == "EXCEPT":
            if any(match(v) for v in (getattr(item, "patterns", None) or [])):
                return True
            ex_assign = getattr(item, "assign", None)
            if ex_assign and match(ex_assign):
                return True
        elif t == "GROUP":
            if match(getattr(item, "name", None)):
                return True

        sub = getattr(item, "body", None)
        if sub and _raw_body_matches(sub, match):
            return True
    return False


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
        tags=[normalize(str(t), ignore="_") for t in test.tags] if getattr(test, "tags", None) else None,
        elapsed_seconds=_elapsed_seconds(test),
        start_time=_iso(_start_time(test)),
        source=src_str,
        rel_source=None if full_paths else rel_src,
        lineno=getattr(test, "lineno", None) or None,
    )


def _collect_failures(
    suite: Any,
    status_filters: Tuple[str, ...],
    *,
    full_paths: bool = False,
    match: Optional["_SearchMatcher"] = None,
) -> List[TestResultItem]:
    """Return all failed tests (post-tree-filter, after status filter) with msgs."""
    wanted = _normalise_statuses(status_filters)
    out: List[TestResultItem] = []
    for t in _iter_all_tests(suite):
        if wanted and t.status not in wanted:
            continue
        if t.status != "FAIL":
            continue
        if match is not None and not _raw_test_search_matches(t, match):
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
            "start_time": _iso(_start_time(item)),
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
            iter_vars = _loop_variables(item) if isinstance(item, ForIteration) else None
            return LogEntry(
                type="ITERATION",
                assign=list(iter_vars or []) or None,
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
