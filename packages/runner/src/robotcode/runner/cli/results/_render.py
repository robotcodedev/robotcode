"""click.style-based renderers for `robotcode results` TEXT-mode output.

Per-entry single line with a colored status prefix, bold name, parenthesised
`(path:line)` suffix (which VS Code's terminal link detector picks up
natively), plus a `Statistics:` footer with bold blue labels.

Renderers yield strings so they can stream into `app.echo_via_pager(...)`.
`click.style` handles colour vs. no-colour automatically based on the
configured `color` flag in `echo_via_pager`.
"""

import os
from typing import Any, Callable, Dict, Iterable, List, Optional

import click

from .._search import make_highlighter
from ._models import (
    ArtifactRef,
    DiffChange,
    DiffResult,
    LogEntry,
    LogResult,
    ShowResult,
    StatsResult,
    StatsSection,
    SummaryResult,
    TestResultItem,
)

_STATUS_COLOR = {
    "PASS": "green",
    "FAIL": "red",
    "SKIP": "yellow",
    "NOT RUN": "white",
    "NOT SET": "white",
}

_LEVEL_COLOR = {
    "WARN": "yellow",
    "ERROR": "red",
    "FAIL": "red",
}

_LEVEL_ORDER = {"TRACE": 0, "DEBUG": 1, "INFO": 2, "WARN": 3, "ERROR": 4, "FAIL": 5}
_LEVEL_RANK = {"FAIL": 0, "ERROR": 1, "WARN": 2}


def _status_badge(status: str) -> str:
    """Left-aligned, padded status badge (for column-aligned lists)."""
    label = f"{status:<7}"  # widest is "NOT RUN" → 7 chars
    color = _STATUS_COLOR.get(status.upper())
    return click.style(label, fg=color, bold=True) if color else label


def _status_inline(status: str) -> str:
    """Fit-width status badge (for inline use, no trailing padding)."""
    color = _STATUS_COLOR.get(status.upper())
    return click.style(status, fg=color, bold=True) if color else status


def _level_badge(level: str) -> str:
    label = f"[{level:<5}]"  # widest is "TRACE" → 5 chars
    color = _LEVEL_COLOR.get(level.upper())
    return click.style(label, fg=color, bold=color is not None) if color else label


def _fmt_elapsed(seconds: Optional[float]) -> str:
    if seconds is None:
        return "n/a"
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    minutes, sec = divmod(seconds, 60)
    return f"{int(minutes)} min {sec:.1f} s"


def _fmt_timestamp(iso: Optional[str]) -> str:
    """Render an ISO 8601 timestamp as `YYYY-MM-DD HH:MM:SS` for humans."""
    if not iso:
        return ""
    try:
        from datetime import datetime

        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return iso


def _fmt_time_only(iso: Optional[str]) -> str:
    """Render only the `HH:MM:SS` part of an ISO 8601 timestamp."""
    if not iso:
        return ""
    try:
        from datetime import datetime

        return datetime.fromisoformat(iso).strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return iso


def _timing_suffix(
    elapsed_seconds: Optional[float],
    start_time: Optional[str],
    *,
    show_timing: bool,
) -> str:
    """Return a dim parenthesised timing suffix or an empty string.

    Without `show_timing`: `(12 ms)` when elapsed is known, else "".
    With `show_timing`:    `(13:34:23 · 12 ms)` when both are known.
    """
    parts: List[str] = []
    if show_timing and start_time:
        parts.append(_fmt_time_only(start_time))
    if elapsed_seconds is not None:
        parts.append(_fmt_elapsed(elapsed_seconds))
    if not parts:
        return ""
    return click.style(f"  ({' · '.join(parts)})", dim=True)


def _fmt_msg_counts(counts: Dict[str, int]) -> str:
    items = [(lvl, n) for lvl, n in counts.items() if n]
    items.sort(key=lambda kv: _LEVEL_RANK.get(kv[0], 99))
    return ", ".join(f"{n} {lvl}" for lvl, n in items)


def _format_filters(filters: Dict[str, List[str]]) -> str:
    return "; ".join(f"{k}={', '.join(v)}" for k, v in filters.items() if v)


def _source_paren(t: TestResultItem, *, full_paths: bool) -> str:
    path = t.source if full_paths else (t.rel_source or t.source)
    if not path:
        return ""
    return f" ({path}:{t.lineno or 1})"


def _message_color(status: str) -> Optional[str]:
    """Pick a colour for the inline failure/skip message under a test entry."""
    status_upper = status.upper()
    if status_upper == "FAIL":
        return "red"
    if status_upper == "SKIP":
        return "yellow"
    return None


def _format_test_entry(
    t: TestResultItem,
    *,
    full_paths: bool,
    show_timing: bool = False,
    highlight: Optional[Callable[[str], str]] = None,
) -> Iterable[str]:
    """Yield one line per test: `<STATUS> name (path:line)` + indented msg."""
    yield _status_badge(t.status)
    yield " "
    name = highlight(t.full_name) if highlight else t.full_name
    yield click.style(name, bold=True)
    yield _source_paren(t, full_paths=full_paths)
    if show_timing:
        yield _timing_suffix(t.elapsed_seconds, t.start_time, show_timing=show_timing)
    yield os.linesep
    if t.message:
        color = _message_color(t.status)
        for line in t.message.splitlines():
            styled = highlight(line) if highlight else line
            yield "        "
            yield click.style(styled, fg=color, italic=True) if color else click.style(styled, italic=True)
            yield os.linesep


def _format_stats_row(label: str, value: str, *, width: int) -> Iterable[str]:
    yield click.style(f"  - {label:<{width}}", bold=True, fg="blue")
    yield value
    yield os.linesep


def render_summary(data: SummaryResult, *, full_paths: bool = False) -> Iterable[str]:
    name = data.file.rel_source or data.file.source

    if data.failures:
        yield click.style(f"Failures ({len(data.failures)}):", underline=True, fg="blue")
        yield os.linesep
        for t in data.failures:
            yield from _format_test_entry(t, full_paths=full_paths)
        yield os.linesep

    yield click.style("Summary: ", underline=True, fg="blue")
    yield name
    yield os.linesep

    rows: List[tuple[str, str]] = [
        ("Status", _status_inline(data.status)),
        ("Total", str(data.counts.total)),
        ("Passed", str(data.counts.passed)),
        ("Failed", str(data.counts.failed)),
        ("Skipped", str(data.counts.skipped)),
    ]
    if data.counts.not_run:
        rows.append(("Not run", str(data.counts.not_run)))
    if data.start_time:
        rows.append(("Started", _fmt_timestamp(data.start_time)))
    if data.end_time:
        rows.append(("Ended", _fmt_timestamp(data.end_time)))
    if data.elapsed_seconds is not None:
        rows.append(("Elapsed", _fmt_elapsed(data.elapsed_seconds)))
    if data.messages_count:
        rows.append(("Messages", _fmt_msg_counts(data.messages_count)))

    label_width = max(len(label) for label, _ in rows) + 2
    for label, value in rows:
        yield from _format_stats_row(label + ":", value, width=label_width)

    if data.filters_applied:
        yield os.linesep
        yield click.style("  Filters: ", bold=True, fg="blue")
        yield _format_filters(data.filters_applied)
        yield os.linesep


def render_show(
    data: ShowResult,
    *,
    show_tags: bool,
    full_paths: bool = False,
    show_timing: bool = False,
    sort_field: Optional[str] = None,
    reverse: bool = False,
    search_substring: Optional[str] = None,
    search_regex: Optional[str] = None,
) -> Iterable[str]:
    name = data.file.rel_source or data.file.source
    highlight = make_highlighter(search_substring, search_regex)

    if not data.tests:
        if data.filters_applied:
            yield click.style("No tests matched filters: ", fg="yellow")
            yield _format_filters(data.filters_applied)
        else:
            yield click.style("(no tests in result file)", dim=True)
        yield os.linesep
        return

    for t in data.tests:
        yield from _format_test_entry(t, full_paths=full_paths, show_timing=show_timing, highlight=highlight)
        if show_tags and t.tags:
            yield "        "
            yield click.style("Tags: ", bold=True, fg="blue")
            yield ", ".join((highlight(tag) if highlight else tag) for tag in t.tags)
            yield os.linesep

    if data.truncated:
        yield os.linesep
        yield click.style(
            f"… {data.truncated} more not shown (use `--top 0` for all)",
            dim=True,
        )
        yield os.linesep

    yield os.linesep
    yield click.style("Statistics: ", underline=True, fg="blue")
    yield name
    yield os.linesep

    rows: List[tuple[str, str]] = [
        ("Total", str(data.counts.total)),
        ("Passed", str(data.counts.passed)),
        ("Failed", str(data.counts.failed)),
        ("Skipped", str(data.counts.skipped)),
    ]
    if data.counts.not_run:
        rows.append(("Not run", str(data.counts.not_run)))
    if show_timing:
        if data.start_time:
            rows.append(("Started", _fmt_timestamp(data.start_time)))
        if data.end_time:
            rows.append(("Ended", _fmt_timestamp(data.end_time)))
        if data.elapsed_seconds is not None:
            rows.append(("Elapsed", _fmt_elapsed(data.elapsed_seconds)))
    label_width = max(len(label) for label, _ in rows) + 2
    for label, value in rows:
        yield from _format_stats_row(label + ":", value, width=label_width)

    if data.filters_applied:
        yield os.linesep
        yield click.style("  Filters: ", bold=True, fg="blue")
        yield _format_filters(data.filters_applied)
        yield os.linesep

    if sort_field:
        natural_desc = sort_field.lower() == "elapsed"
        direction = "desc" if natural_desc ^ reverse else "asc"
        yield click.style(f"Sorted by {sort_field.lower()} ({direction})", dim=True, italic=True)
        yield os.linesep


_STATS_DIMENSION_HEADING = {
    "tag": "By Tag",
    "suite": "By Suite",
    "status": "By Status",
}


def render_stats(data: StatsResult) -> Iterable[str]:
    sections = data.sections
    if not sections:
        yield click.style("(no aggregation dimensions selected)", dim=True)
        yield os.linesep
        return

    for idx, section in enumerate(sections):
        if idx:
            yield os.linesep
        heading = _STATS_DIMENSION_HEADING.get(section.dimension, section.dimension.title())
        yield click.style(f"{heading}:", underline=True, fg="blue")
        yield os.linesep

        if not section.groups:
            yield "    "
            yield click.style("(no groups matched)", dim=True, italic=True)
            yield os.linesep
            continue

        yield from _render_stats_table(section)

        if section.truncated:
            yield "    "
            yield click.style(
                f"… {section.truncated} more not shown (use `--top 0` for all)",
                dim=True,
            )
            yield os.linesep

    if data.filters_applied:
        yield os.linesep
        yield click.style("  Filters: ", bold=True, fg="blue")
        yield _format_filters(data.filters_applied)
        yield os.linesep


def _render_stats_table(section: StatsSection) -> Iterable[str]:
    name_header = "STATUS" if section.dimension == "status" else "NAME"
    headers = [name_header, "TOTAL", "PASS", "FAIL", "SKIP", "ELAPSED"]
    rows = []
    for g in section.groups:
        rows.append(
            [
                g.name,
                str(g.counts.total),
                str(g.counts.passed),
                str(g.counts.failed),
                str(g.counts.skipped),
                _fmt_elapsed(g.elapsed_seconds) if g.elapsed_seconds is not None else "",
            ]
        )
    widths = [max(len(headers[i]), max((len(r[i]) for r in rows), default=0)) for i in range(len(headers))]

    def _fmt_cell(text: str, width: int, align: str = "left") -> str:
        return text.ljust(width) if align == "left" else text.rjust(width)

    aligns = ["left", "right", "right", "right", "right", "right"]
    yield "    "
    yield "  ".join(_fmt_cell(headers[i], widths[i], aligns[i]) for i in range(len(headers)))
    yield os.linesep

    for r, g in zip(rows, section.groups):
        name_cell = _fmt_cell(r[0], widths[0])
        if section.dimension == "status":
            name_cell = click.style(name_cell, **_status_style(g.name))
        cells = [
            name_cell,
            _fmt_cell(r[1], widths[1], "right"),
            _colored_count(r[2], widths[2], g.counts.passed, "green"),
            _colored_count(r[3], widths[3], g.counts.failed, "red"),
            _colored_count(r[4], widths[4], g.counts.skipped, "yellow"),
            _fmt_cell(r[5], widths[5], "right"),
        ]
        yield "    "
        yield "  ".join(cells)
        yield os.linesep


def _colored_count(text: str, width: int, value: int, color: str) -> str:
    cell = text.rjust(width)
    return click.style(cell, fg=color) if value else cell


def _status_style(status: str) -> Dict[str, Any]:
    color = _STATUS_COLOR.get(status)
    return {"fg": color, "bold": True} if color else {}


_DIFF_SECTION_META = [
    ("new_failures", "New failures", "❌", "red"),
    ("new_passes", "New passes", "✅", "green"),
    ("status_changes", "Status changes", "⚠", "yellow"),
    ("added", "Added in current", "+", "cyan"),
    ("removed", "Removed from current", "-", "magenta"),
]


def render_diff(data: DiffResult, *, full_paths: bool = False) -> Iterable[str]:
    baseline_label = data.baseline.rel_source or data.baseline.source
    current_label = data.current.rel_source or data.current.source
    yield click.style("Diff: ", underline=True, fg="blue")
    yield baseline_label
    yield " → "
    yield current_label
    yield os.linesep

    summary_counts: Dict[str, int] = {}

    for attr, heading, marker, color in _DIFF_SECTION_META:
        items: Optional[List[DiffChange]] = getattr(data, attr)
        if not items:
            continue
        summary_counts[heading] = len(items)
        yield os.linesep
        yield click.style(f"{heading} ({len(items)}):", bold=True, fg=color)
        yield os.linesep
        for change in items:
            yield from _render_diff_change(change, marker=marker, color=color, full_paths=full_paths)

    if not summary_counts:
        yield os.linesep
        yield click.style("No differences.", dim=True)
        yield os.linesep
        return

    yield os.linesep
    yield click.style("Summary: ", bold=True, fg="blue")
    yield ", ".join(f"{count} {label.lower()}" for label, count in summary_counts.items())
    yield "."
    yield os.linesep


def _render_diff_change(change: DiffChange, *, marker: str, color: str, full_paths: bool) -> Iterable[str]:
    yield "  "
    yield click.style(marker, fg=color, bold=True)
    yield " "
    yield click.style(change.full_name, bold=True)

    if change.source:
        path = change.source if full_paths else (change.rel_source or change.source)
        yield f" ({path}:{change.lineno or 1})"

    if change.baseline_status and change.current_status:
        yield "    "
        yield _status_inline(change.baseline_status)
        yield " → "
        yield _status_inline(change.current_status)
    elif change.current_status:
        yield "    "
        yield _status_inline(change.current_status)
    elif change.baseline_status:
        yield "    "
        yield _status_inline(change.baseline_status)
    yield os.linesep

    msg = change.current_message or change.baseline_message
    if msg:
        for line in msg.splitlines():
            yield "    > "
            yield click.style(line, italic=True, dim=True)
            yield os.linesep


_CONTROL_TYPES = {
    "FOR",
    "WHILE",
    "IF",
    "ELSE IF",
    "ELSE",
    "TRY",
    "EXCEPT",
    "FINALLY",
    "ITERATION",
    "GROUP",
    "VAR",
    "RETURN",
    "CONTINUE",
    "BREAK",
    "ERROR",
}


def render_log(
    data: LogResult,
    *,
    full_paths: bool = False,
    level: str = "INFO",
    max_depth: int = 0,
    show_timestamps: bool = False,
    show_timing: bool = False,
    search_substring: Optional[str] = None,
    search_regex: Optional[str] = None,
) -> Iterable[str]:
    threshold = _LEVEL_ORDER.get(level.upper(), 2)
    highlight = make_highlighter(search_substring, search_regex)

    if not data.tests and not data.execution_messages:
        yield click.style("(no tests matched)", dim=True)
        yield os.linesep
        return

    for i, t in enumerate(data.tests):
        if i:
            yield os.linesep
        yield click.style("Test: ", fg="blue")
        full_name = highlight(t.full_name) if highlight else t.full_name
        yield click.style(full_name, bold=True)
        if t.source:
            path = t.source if full_paths else (t.rel_source or t.source)
            yield f" ({path}:{t.lineno or 1})"
        yield " "
        yield _status_inline(t.status)
        yield _timing_suffix(
            getattr(t, "elapsed_seconds", None),
            getattr(t, "start_time", None),
            show_timing=show_timing,
        )
        yield os.linesep

        if t.message:
            color = _message_color(t.status)
            for line in t.message.splitlines():
                styled = highlight(line) if highlight else line
                yield "  > "
                yield (click.style(styled, fg=color, italic=True) if color else click.style(styled, italic=True))
                yield os.linesep

        yield from _render_entries(
            t.body or [],
            depth=1,
            kw_depth=0,
            max_depth=max_depth,
            threshold=threshold,
            show_timestamps=show_timestamps,
            show_timing=show_timing,
            full_paths=full_paths,
            highlight=highlight,
        )

    if data.execution_messages:
        if data.tests:
            yield os.linesep
        yield click.style(
            f"Execution messages ({len(data.execution_messages)}):",
            underline=True,
            fg="blue",
        )
        yield os.linesep
        for msg in data.execution_messages:
            yield "  "
            yield _level_badge(msg.level or "INFO")
            if show_timestamps and msg.timestamp:
                yield f" [{msg.timestamp}]"
            yield " "
            text = msg.text or ""
            yield highlight(text) if highlight else text
            yield os.linesep

    if data.extract_dir and data.extracted_count:
        yield os.linesep
        yield click.style("Extracted: ", bold=True, fg="blue")
        yield f"{data.extracted_count} artefact(s) → {data.extract_dir}"
        yield os.linesep

    if show_timing and (data.start_time or data.end_time or data.elapsed_seconds is not None):
        time_rows: List[tuple[str, str]] = []
        if data.start_time:
            time_rows.append(("Started", _fmt_timestamp(data.start_time)))
        if data.end_time:
            time_rows.append(("Ended", _fmt_timestamp(data.end_time)))
        if data.elapsed_seconds is not None:
            time_rows.append(("Elapsed", _fmt_elapsed(data.elapsed_seconds)))
        yield os.linesep
        width = max(len(label) for label, _ in time_rows) + 2
        for label, value in time_rows:
            yield from _format_stats_row(label + ":", value, width=width)


_KEYWORD_ENTRY_TYPES = {"KEYWORD", "SETUP", "TEARDOWN"}


def _render_entries(
    entries: List[LogEntry],
    *,
    depth: int,
    kw_depth: int,
    max_depth: int,
    threshold: int,
    show_timestamps: bool,
    show_timing: bool,
    full_paths: bool,
    highlight: Optional[Callable[[str], str]] = None,
) -> Iterable[str]:
    """Render each entry on a header line with its children indented below."""
    for entry in entries:
        yield from _render_entry(
            entry,
            depth=depth,
            kw_depth=kw_depth,
            max_depth=max_depth,
            threshold=threshold,
            show_timestamps=show_timestamps,
            show_timing=show_timing,
            full_paths=full_paths,
            highlight=highlight,
        )


def _render_entry(
    entry: LogEntry,
    *,
    depth: int,
    kw_depth: int,
    max_depth: int,
    threshold: int,
    show_timestamps: bool,
    show_timing: bool,
    full_paths: bool,
    highlight: Optional[Callable[[str], str]] = None,
) -> Iterable[str]:
    indent = "  " * depth
    etype = entry.type

    if etype == "MESSAGE":
        lvl = (entry.level or "INFO").upper()
        if _LEVEL_ORDER.get(lvl, 2) < threshold:
            return
        yield indent
        yield _level_badge(lvl)
        if show_timestamps and entry.timestamp:
            yield f" [{entry.timestamp}]"
        yield " "
        text = entry.text or ""
        lines = text.splitlines() or [""]
        for j, line in enumerate(lines):
            styled_line = highlight(line) if highlight else line
            if j == 0:
                yield styled_line
            else:
                yield os.linesep
                yield indent
                yield "       "  # align under level badge
                yield styled_line
        yield os.linesep
        if entry.artifacts:
            yield from _render_artifacts(entry.artifacts, indent=indent + "  ", full_paths=full_paths)
        return

    yield indent
    yield from _format_entry_header(entry, show_timing=show_timing, highlight=highlight)
    yield os.linesep

    if entry.message and entry.status in ("FAIL", "SKIP"):
        color = _message_color(entry.status)
        for line in entry.message.splitlines():
            styled = highlight(line) if highlight else line
            yield indent
            yield "  > "
            yield (click.style(styled, fg=color, italic=True) if color else click.style(styled, italic=True))
            yield os.linesep

    if not entry.body:
        return

    is_call = etype in _KEYWORD_ENTRY_TYPES
    new_kw_depth = kw_depth + 1 if is_call else kw_depth
    if is_call and max_depth > 0 and new_kw_depth >= max_depth:
        hidden = _count_hidden(entry.body)
        if hidden:
            yield indent + "  "
            yield click.style(
                f"… {hidden} hidden (--max-depth {max_depth})",
                dim=True,
                italic=True,
            )
            yield os.linesep
        return

    yield from _render_entries(
        entry.body,
        depth=depth + 1,
        kw_depth=new_kw_depth,
        max_depth=max_depth,
        threshold=threshold,
        show_timestamps=show_timestamps,
        show_timing=show_timing,
        full_paths=full_paths,
        highlight=highlight,
    )


def _count_hidden(entries: List[LogEntry]) -> int:
    """Total number of body items (keywords + messages + control structures) recursively."""
    total = 0
    for e in entries:
        total += 1
        if e.body:
            total += _count_hidden(e.body)
    return total


def _format_entry_header(
    entry: LogEntry,
    *,
    show_timing: bool = False,
    highlight: Optional[Callable[[str], str]] = None,
) -> Iterable[str]:
    """Yield the styled header line for a non-MESSAGE entry (no newline)."""
    t = entry.type

    def _hi(s: str) -> str:
        return highlight(s) if highlight else s

    if t in ("KEYWORD", "SETUP", "TEARDOWN"):
        label_prefix = "" if t == "KEYWORD" else f"[{t}] "
        if label_prefix:
            yield click.style(label_prefix, fg="cyan", bold=True)
        if entry.assign:
            yield click.style("  ".join(_hi(a) for a in entry.assign) + "  ", fg="magenta")
        if entry.name:
            yield click.style(_hi(entry.name), bold=True)
        if entry.args:
            yield "    "
            yield "    ".join(_hi(a) for a in entry.args)
    elif t == "FOR":
        yield click.style("FOR", fg="cyan", bold=True)
        if entry.assign:
            yield "    "
            yield "    ".join(click.style(v, fg="magenta") for v in entry.assign)
        if entry.flavor:
            yield "    "
            yield click.style(entry.flavor, fg="cyan", bold=True)
        if entry.args:
            yield "    "
            yield "    ".join(entry.args)
    elif t == "ITERATION":
        yield click.style("ITER", fg="cyan", bold=True)
        if entry.assign:
            yield "    "
            yield "    ".join(click.style(v, fg="magenta") for v in entry.assign)
    elif t == "WHILE":
        yield click.style("WHILE", fg="cyan", bold=True)
        if entry.condition:
            yield "    "
            yield entry.condition
    elif t in ("IF", "ELSE IF"):
        yield click.style(t, fg="cyan", bold=True)
        if entry.condition:
            yield "    "
            yield entry.condition
    elif t == "ELSE":
        yield click.style("ELSE", fg="cyan", bold=True)
    elif t == "TRY":
        yield click.style("TRY", fg="cyan", bold=True)
    elif t == "EXCEPT":
        yield click.style("EXCEPT", fg="cyan", bold=True)
        if entry.patterns:
            yield "    "
            yield "    ".join(entry.patterns)
        if entry.pattern_type:
            yield click.style(f"  type={entry.pattern_type}", dim=True)
        if entry.assign:
            yield "    AS    "
            yield click.style("  ".join(entry.assign), fg="magenta")
    elif t == "FINALLY":
        yield click.style("FINALLY", fg="cyan", bold=True)
    elif t == "VAR":
        yield click.style("VAR", fg="cyan", bold=True)
        if entry.assign:
            yield "    "
            yield click.style(entry.assign[0], fg="magenta")
        if entry.args:
            yield "    "
            yield "    ".join(entry.args)
        if entry.scope and entry.scope.upper() != "LOCAL":
            yield click.style(f"  scope={entry.scope}", dim=True)
        if entry.separator is not None:
            yield click.style(f"  separator={entry.separator!r}", dim=True)
    elif t == "RETURN":
        yield click.style("RETURN", fg="cyan", bold=True)
        if entry.args:
            yield "    "
            yield "    ".join(entry.args)
    elif t in ("CONTINUE", "BREAK"):
        yield click.style(t, fg="cyan", bold=True)
    elif t == "GROUP":
        yield click.style("GROUP", fg="cyan", bold=True)
        if entry.name:
            yield "    "
            yield click.style(entry.name, bold=True)
    elif t == "ERROR":
        yield click.style("ERROR", fg="red", bold=True)
        if entry.args:
            yield "    "
            yield "    ".join(entry.args)
    else:
        yield click.style(t, fg="cyan", bold=True)
        if entry.name:
            yield "    "
            yield entry.name

    if entry.status and entry.status != "NOT SET":
        yield "    "
        yield _status_inline(entry.status)
    if (entry.elapsed_seconds is not None and entry.elapsed_seconds > 0) or (show_timing and entry.start_time):
        yield _timing_suffix(entry.elapsed_seconds, entry.start_time, show_timing=show_timing)


def _artefact_display(ref: ArtifactRef, *, full_paths: bool) -> str:
    """Pick the best display path for an artefact.

    With `full_paths=True` → the absolute `resolved_path`.
    Otherwise prefer `rel_path` (relative to the output file's directory) and
    fall back to `resolved_path` if no relative path is known.
    """
    if ref.extracted_to:
        return ref.extracted_to
    if full_paths:
        return ref.resolved_path or ref.src
    return ref.rel_path or ref.resolved_path or ref.src


def _render_artifacts(artefacts: List[ArtifactRef], *, indent: str, full_paths: bool = False) -> Iterable[str]:
    for ref in artefacts:
        yield indent
        if ref.skipped_reason:
            yield click.style(
                f"(skipped {ref.kind} '{ref.src}': {ref.skipped_reason})",
                fg="yellow",
                dim=True,
            )
            yield os.linesep
            continue
        emoji = "image:" if ref.kind == "image" else "file: "
        if ref.embedded:
            size = ""
            if ref.approx_bytes is not None:
                size = f", {_fmt_bytes(ref.approx_bytes)}"
            mt = f"{ref.media_type or ref.kind}{size}"
            if ref.extracted_to:
                yield click.style(emoji, fg="cyan")
                yield " "
                yield _artefact_display(ref, full_paths=full_paths)
                yield click.style(f" (extracted, {mt})", dim=True)
            else:
                yield click.style(emoji, fg="cyan")
                yield click.style(f" embedded {mt} — use --extract to save", dim=True)
        elif ref.resolved_path:
            yield click.style(emoji, fg="cyan")
            yield " "
            yield _artefact_display(ref, full_paths=full_paths)
        else:
            yield click.style(emoji, fg="cyan")
            yield " "
            yield ref.src
            yield click.style(" (unresolved)", dim=True)
        yield os.linesep


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "kB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n = int(n / 1024)
    return f"{n:.1f} TB"
