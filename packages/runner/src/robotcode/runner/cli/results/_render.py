"""Markdown renderers for `robotcode results` TEXT-mode output.

Each `render_*` returns a single markdown string. The caller pipes it
through `app.echo_as_markdown(...)`, which decides between two paths:

- **Colored TTY**: `rich` renders the markdown to themed ANSI and pages
  if longer than the terminal.
- **No color / pipe / `--no-color`**: raw markdown is emitted verbatim —
  pipe-friendly, LLM-friendly, and pastable into Slack / GitHub PRs.

Inline `(path:line)` references stay as plain text so VS Code's terminal
link detector still picks them up; status names are bold (`**FAIL**`)
rather than inline-coloured so the same markdown reads cleanly in every
display target.
"""

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from ._models import (
    ArtifactRef,
    DiffChange,
    DiffResult,
    LogEntry,
    LogResult,
    LogSuite,
    LogTest,
    ShowResult,
    StatsResult,
    StatsSection,
    SummaryResult,
    TestResultItem,
)

# `TestResultItem` is the canonical per-test record (used by `summary` and
# `show`); `LogTest` is the `log`-specific record carrying a body tree.
# Both expose the fields the per-test renderers need (`full_name`,
# `status`, `message`, `source`, `rel_source`, `lineno`, `elapsed_seconds`,
# `start_time`), so we treat them interchangeably at the renderer level.
_TestLike = Union[TestResultItem, LogTest]

_LEVEL_ORDER = {"TRACE": 0, "DEBUG": 1, "INFO": 2, "WARN": 3, "ERROR": 4, "FAIL": 5}
_LEVEL_RANK = {"FAIL": 0, "ERROR": 1, "WARN": 2}

_KEYWORD_ENTRY_TYPES = {"KEYWORD", "SETUP", "TEARDOWN"}

_STATS_DIMENSION_HEADING = {
    "tag": "By Tag",
    "suite": "By Suite",
    "status": "By Status",
}

# (attr name, heading text) — order is the rendering order of diff sections.
_DIFF_SECTION_META = [
    ("new_failures", "New failures"),
    ("new_passes", "New passes"),
    ("status_changes", "Status changes"),
    ("added", "Added in current"),
    ("removed", "Removed from current"),
]


# ---------------------------------------------------------------------------
# Formatters (pure)
# ---------------------------------------------------------------------------


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


def _fmt_msg_counts(counts: Dict[str, int]) -> str:
    items = [(lvl, n) for lvl, n in counts.items() if n]
    items.sort(key=lambda kv: _LEVEL_RANK.get(kv[0], 99))
    return ", ".join(f"{n} {lvl}" for lvl, n in items)


def _format_filters(filters: Dict[str, List[str]]) -> str:
    return "; ".join(f"{k}={', '.join(v)}" for k, v in filters.items() if v)


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "kB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n = int(n / 1024)
    return f"{n:.1f} TB"


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


# Characters that have markdown meaning anywhere in a line — escape them
# in arbitrary user content (test names, tags, messages). We deliberately
# leave alone:
# - `#`, `+`, `-`, `!`: only special at the start of a line, and the
#   renderer never places user data there.
# - `|`: escaped separately by `_md_pipe` (only matters inside tables).
# - `_`: CommonMark disables intraword underscore emphasis, so identifiers
#   like `KW_DOC_TOKEN_beta` or `${var_name}` stay literal without escapes.
_MD_ESCAPE_RE = re.compile(r"([\\`*\[\]])")


def _md_escape(text: str) -> str:
    """Escape markdown metacharacters in arbitrary user content (test names,
    tags, paths). Safe to apply even when the content has no specials."""
    return _MD_ESCAPE_RE.sub(r"\\\1", text)


def _md_pipe(text: str) -> str:
    """Escape only the table-cell separator for use inside markdown tables."""
    return text.replace("|", "\\|")


def _path_paren(
    *,
    source: Optional[str],
    rel_source: Optional[str],
    lineno: Optional[int],
    full_paths: bool,
) -> str:
    """Trailing `(path:line)` suffix VS Code's terminal link detector
    picks up. Pass ``lineno=None`` for `(path)` without a line marker
    (e.g. on suite headers). Empty string when no path is available."""
    path = source if full_paths else (rel_source or source)
    if not path:
        return ""
    if lineno is None:
        return f" ({path})"
    return f" ({path}:{lineno})"


def _source_paren(t: _TestLike, *, full_paths: bool) -> str:
    """`_path_paren` wrapper for any per-test record (`TestResultItem` /
    `LogTest`). Defaults a missing `lineno` to 1 — the convention for
    test source references where `(path:1)` is friendlier than just
    `(path)`."""
    return _path_paren(source=t.source, rel_source=t.rel_source, lineno=t.lineno or 1, full_paths=full_paths)


def _timing_suffix(
    elapsed_seconds: Optional[float],
    start_time: Optional[str],
    *,
    show_timing: bool,
) -> str:
    """Italic `(13:34:23 · 12 ms)` suffix or an empty string."""
    parts: List[str] = []
    if show_timing and start_time:
        parts.append(_fmt_time_only(start_time))
    if elapsed_seconds is not None:
        parts.append(_fmt_elapsed(elapsed_seconds))
    if not parts:
        return ""
    return f" _({' · '.join(parts)})_"


def _md_table(headers: List[str], rows: List[List[str]], *, aligns: Optional[List[str]] = None) -> str:
    """Render a markdown table with per-column padding.

    Cells are space-padded to the widest entry in each column (header
    included) so the raw markdown source lines up in a fixed-width
    terminal — the form that goes through on `--no-color` or in a pipe.
    Markdown renderers like `rich` strip the whitespace and lay the
    table out themselves, so the padding costs nothing there.

    `aligns` is per-column: ``"left"``, ``"right"``, or ``"center"``.
    """
    if aligns is None:
        aligns = ["left"] * len(headers)

    escaped_rows = [[_md_pipe(cell) for cell in r] for r in rows]
    # Per-column visual width = max(header, all cells). Display-width-aware
    # so emoji cells (counted as 2 terminal columns) don't under-pad the
    # column. Floor at 3 so the `---` separator stays valid for narrow
    # columns like a one-digit count.
    widths: List[int] = []
    for col, header in enumerate(headers):
        w = _display_width(header)
        for r in escaped_rows:
            if col < len(r):
                w = max(w, _display_width(r[col]))
        widths.append(max(w, 3))

    def _pad(text: str, width: int, align: str) -> str:
        extra = width - _display_width(text)
        if extra <= 0:
            return text
        if align == "right":
            return " " * extra + text
        if align == "center":
            left = extra // 2
            return " " * left + text + " " * (extra - left)
        return text + " " * extra

    def _sep(width: int, align: str) -> str:
        if align == "right":
            return "-" * (width - 1) + ":"
        if align == "center":
            return ":" + "-" * (width - 2) + ":"
        return "-" * width

    lines = [
        "| " + " | ".join(_pad(headers[i], widths[i], aligns[i]) for i in range(len(headers))) + " |",
        "| " + " | ".join(_sep(widths[i], aligns[i]) for i in range(len(headers))) + " |",
    ]
    for r in escaped_rows:
        lines.append("| " + " | ".join(_pad(r[i], widths[i], aligns[i]) for i in range(len(headers))) + " |")
    return "\n".join(lines)


_STATUS_ICONS = {
    "PASS": "✅",
    "FAIL": "❌",
    "SKIP": "⏭",
    "NOT RUN": "⏸",
    "NOT SET": "⚪",
}


def _status_icon(status: str) -> str:
    return _STATUS_ICONS.get(status.upper(), "")


def _bold_status(status: str, *, icon: bool = True) -> str:
    """Icon + bold status word: ``❌ **FAIL**``. The icon gives a scanable
    visual marker for terminal / Slack / GitHub paste; the bold word keeps
    the status readable for screen readers and stays meaningful in
    rendering targets that don't paint emoji. Pass ``icon=False`` to
    suppress the emoji (e.g. when the cell is followed by a separator or
    you want to stay strictly ASCII)."""
    word = f"**{status.upper()}**"
    if icon:
        ic = _status_icon(status)
        if ic:
            return f"{ic} {word}"
    return word


# Display-width adjustment for the (small, fixed) emoji set the renderer
# emits. Most emoji codepoints render as two terminal cells but `len()`
# counts them as one — so naive padding under-pads any row containing
# an emoji. We explicitly track the icons we use rather than a regex
# range, because the misc-technical block (U+2300..U+23FF) holds both
# double-width emoji (`⏭`, `⏸`) and single-width geometric shapes —
# a range-based heuristic would either miss our icons or misclassify
# unrelated content.
_DOUBLE_WIDTH_ICONS: "frozenset[str]" = frozenset(_STATUS_ICONS.values())


def _display_width(text: str) -> int:
    """Source length plus one extra column per known double-width emoji."""
    return len(text) + sum(1 for ch in text if ch in _DOUBLE_WIDTH_ICONS)


def _highlight_md(text: str, highlight: Optional[Callable[[str], str]]) -> str:
    """Apply the search-highlight callback if any; the renderer wraps matches
    in inline-code spans (`` `match` ``) for markdown — visually distinct,
    portable, no terminal-specific escapes."""
    return highlight(text) if highlight else text


# Markdown-flavoured search highlighter. Mirrors the substring-vs-regex
# selection logic of `_search.make_highlighter` but wraps each match in
# inline-code spans (`` `match` ``) instead of click's ANSI inverse —
# inline code renders distinct in `rich` and survives raw-markdown paste.
def _make_md_highlighter(
    search_substring: Optional[str], search_regex: Optional[str]
) -> Optional[Callable[[str], str]]:
    if not search_substring and not search_regex:
        return None
    if search_regex:
        flags = 0
        raw = search_regex
    else:
        flags = re.IGNORECASE
        raw = re.escape(search_substring or "")
    try:
        rx = re.compile(raw, flags)
    except re.error:
        return None

    def wrap_match(m: "re.Match[str]") -> str:
        # Backticks inside the match would break the inline-code span;
        # markdown-escape them so the surrounding `` … `` still renders.
        inner = m.group(0).replace("`", "\\`")
        return "`" + inner + "`"

    def highlight(text: str) -> str:
        if not text:
            return text
        return rx.sub(wrap_match, text)

    return highlight


# ---------------------------------------------------------------------------
# Renderers — one per subcommand
# ---------------------------------------------------------------------------


def render_summary(data: SummaryResult, *, full_paths: bool = False) -> str:
    name = data.file.rel_source or data.file.source or "(unknown source)"
    out: List[str] = []
    out.append(f"# Summary — {_md_escape(name)}")

    rows: List[List[str]] = [
        ["Status", _bold_status(data.status)],
        ["Total", str(data.counts.total)],
        ["Passed", str(data.counts.passed)],
        ["Failed", str(data.counts.failed)],
        ["Skipped", str(data.counts.skipped)],
    ]
    if data.counts.not_run:
        rows.append(["Not run", str(data.counts.not_run)])
    if data.start_time:
        rows.append(["Started", _fmt_timestamp(data.start_time)])
    if data.end_time:
        rows.append(["Ended", _fmt_timestamp(data.end_time)])
    if data.elapsed_seconds is not None:
        rows.append(["Elapsed", _fmt_elapsed(data.elapsed_seconds)])
    if data.messages_count:
        rows.append(["Messages", _fmt_msg_counts(data.messages_count)])
    if data.execution_messages_count:
        rows.append(["Execution messages", _fmt_msg_counts(data.execution_messages_count)])

    out.append("")
    out.append(_md_table(["Field", "Value"], rows, aligns=["left", "left"]))

    if data.failed:
        out.append("")
        out.append(f"## Failures ({len(data.failed)})")
        out.append("")
        for t in data.failed:
            out.append(_test_bullet_md(t, full_paths=full_paths))

    if data.filters_applied:
        out.append("")
        out.append(f"_Filters: {_md_escape(_format_filters(data.filters_applied))}_")

    return "\n".join(out) + "\n"


def _test_bullet_md(
    t: _TestLike,
    *,
    full_paths: bool,
    show_timing: bool = False,
    highlight: Optional[Callable[[str], str]] = None,
) -> str:
    """One bullet-item per test: `- STATUS Name (path:line)` with the message
    as a nested blockquote underneath."""
    name = _highlight_md(_md_escape(t.full_name), highlight)
    head = f"- {_bold_status(t.status)} {name}{_source_paren(t, full_paths=full_paths)}"
    if show_timing:
        head += _timing_suffix(t.elapsed_seconds, t.start_time, show_timing=show_timing)
    parts = [head]
    if t.message:
        # Blockquote each line, continuation lines included. Markdown
        # collapses adjacent `>` lines into a single quote block.
        for line in t.message.splitlines() or [t.message]:
            quoted = _highlight_md(_md_escape(line), highlight)
            parts.append(f"  > {quoted}")
    return "\n".join(parts)


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
) -> str:
    name = data.file.rel_source or data.file.source or "(unknown source)"
    highlight = _make_md_highlighter(search_substring, search_regex)
    out: List[str] = []
    out.append(f"# Show — {_md_escape(name)}")
    out.append("")

    if not data.tests:
        if data.filters_applied:
            out.append(f"_No tests matched filters: {_md_escape(_format_filters(data.filters_applied))}_")
        else:
            out.append("_(no tests in result file)_")
        return "\n".join(out) + "\n"

    for t in data.tests:
        out.append(_test_bullet_md(t, full_paths=full_paths, show_timing=show_timing, highlight=highlight))
        if show_tags and t.tags:
            tags = ", ".join(_highlight_md(_md_escape(tag), highlight) for tag in t.tags)
            out.append(f"  - **Tags:** {tags}")

    if data.truncated:
        out.append("")
        out.append(f"_… {data.truncated} more not shown (use `--top 0` for all)_")

    out.append("")
    out.append("## Statistics")
    out.append("")
    stat_rows: List[List[str]] = [
        ["Total", str(data.counts.total)],
        ["Passed", str(data.counts.passed)],
        ["Failed", str(data.counts.failed)],
        ["Skipped", str(data.counts.skipped)],
    ]
    if data.counts.not_run:
        stat_rows.append(["Not run", str(data.counts.not_run)])
    if show_timing:
        if data.start_time:
            stat_rows.append(["Started", _fmt_timestamp(data.start_time)])
        if data.end_time:
            stat_rows.append(["Ended", _fmt_timestamp(data.end_time)])
        if data.elapsed_seconds is not None:
            stat_rows.append(["Elapsed", _fmt_elapsed(data.elapsed_seconds)])
    out.append(_md_table(["Field", "Value"], stat_rows, aligns=["left", "left"]))

    if data.filters_applied:
        out.append("")
        out.append(f"_Filters: {_md_escape(_format_filters(data.filters_applied))}_")

    if sort_field:
        natural_desc = sort_field.lower() == "elapsed"
        direction = "desc" if natural_desc ^ reverse else "asc"
        out.append("")
        out.append(f"_Sorted by {sort_field.lower()} ({direction})_")

    return "\n".join(out) + "\n"


def render_stats(data: StatsResult) -> str:
    out: List[str] = []
    out.append("# Stats")

    sections = data.sections
    if not sections:
        out.append("")
        out.append("_(no aggregation dimensions selected)_")
        return "\n".join(out) + "\n"

    for section in sections:
        heading = _STATS_DIMENSION_HEADING.get(section.dimension, section.dimension.title())
        out.append("")
        out.append(f"## {heading}")
        out.append("")
        if not section.groups:
            out.append("_(no groups matched)_")
            continue
        out.append(_render_stats_table_md(section))
        if section.truncated:
            out.append("")
            out.append(f"_… {section.truncated} more not shown (use `--top 0` for all)_")

    if data.filters_applied:
        out.append("")
        out.append(f"_Filters: {_md_escape(_format_filters(data.filters_applied))}_")

    return "\n".join(out) + "\n"


def _render_stats_table_md(section: StatsSection) -> str:
    name_header = "Status" if section.dimension == "status" else "Name"
    headers = [name_header, "Total", "Pass", "Fail", "Skip", "Elapsed"]
    rows: List[List[str]] = []
    for g in section.groups:
        if section.dimension == "status":
            display_name = _bold_status(g.name)
        else:
            display_name = _md_escape(g.name)
        rows.append(
            [
                display_name,
                str(g.counts.total),
                str(g.counts.passed),
                str(g.counts.failed),
                str(g.counts.skipped),
                _fmt_elapsed(g.elapsed_seconds) if g.elapsed_seconds is not None else "",
            ]
        )
    return _md_table(headers, rows, aligns=["left", "right", "right", "right", "right", "right"])


def render_diff(data: DiffResult, *, full_paths: bool = False) -> str:
    baseline_label = data.baseline.rel_source or data.baseline.source or "(unknown baseline)"
    current_label = data.current.rel_source or data.current.source or "(unknown current)"
    out: List[str] = []
    out.append(f"# Diff — {_md_escape(baseline_label)} → {_md_escape(current_label)}")

    summary_counts: Dict[str, int] = {}
    rendered_any = False

    for attr, heading in _DIFF_SECTION_META:
        items: Optional[List[DiffChange]] = getattr(data, attr)
        if not items:
            continue
        summary_counts[heading] = len(items)
        rendered_any = True
        out.append("")
        out.append(f"## {heading} ({len(items)})")
        out.append("")
        for change in items:
            out.append(_render_diff_change_md(change, full_paths=full_paths))

    if not rendered_any:
        out.append("")
        out.append("_No differences._")
        return "\n".join(out) + "\n"

    out.append("")
    out.append("**Summary:** " + ", ".join(f"{count} {label.lower()}" for label, count in summary_counts.items()) + ".")

    if data.filters_applied:
        out.append("")
        out.append(f"_Filters: {_md_escape(_format_filters(data.filters_applied))}_")

    return "\n".join(out) + "\n"


def _render_diff_change_md(change: DiffChange, *, full_paths: bool) -> str:
    name = _md_escape(change.full_name)
    paren = _path_paren(
        source=change.source,
        rel_source=change.rel_source,
        lineno=change.lineno or 1,
        full_paths=full_paths,
    )
    head = f"- {name}{paren}"

    if change.baseline_status and change.current_status:
        head += f" — {_bold_status(change.baseline_status)} → {_bold_status(change.current_status)}"
    elif change.current_status:
        head += f" — {_bold_status(change.current_status)}"
    elif change.baseline_status:
        head += f" — {_bold_status(change.baseline_status)}"

    parts = [head]
    msg = change.current_message or change.baseline_message
    if msg:
        for line in msg.splitlines() or [msg]:
            parts.append(f"  > {_md_escape(line)}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# `log` — heading per test, body as nested markdown list (keywords +
# control flow), with log messages rendered as inline code spans
# ---------------------------------------------------------------------------


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
    with_suite_info: bool = False,
) -> str:
    threshold = _LEVEL_ORDER.get(level.upper(), 2)
    highlight = _make_md_highlighter(search_substring, search_regex)
    # Anchor for resolving `ArtifactRef.rel_path` (which is stored
    # relative to the output.xml directory). Threaded down through the
    # entry walk so artefact links can be re-expressed relative to cwd
    # — the natural anchor for stdout-rendered markdown.
    output_dir = Path(data.file.source).parent if data.file.source else None

    out: List[str] = []
    out.append("# Log")

    if not data.tests and not data.execution_messages:
        out.append("")
        out.append("_(no tests matched)_")
        return "\n".join(out) + "\n"

    suite_index = {s.full_name: s for s in (data.suites or [])}
    current_suite: Optional[str] = object()  # type: ignore[assignment]

    for t in data.tests:
        if with_suite_info and t.suite != current_suite:
            current_suite = t.suite
            out.append("")
            out.append(_render_suite_header_md(suite_index.get(t.suite or ""), full_paths=full_paths))

        out.append("")
        out.append(_test_header_md(t, full_paths=full_paths, show_timing=show_timing, highlight=highlight))
        if t.message:
            out.append("")
            for line in t.message.splitlines() or [t.message]:
                quoted = _highlight_md(_md_escape(line), highlight)
                out.append(f"> {quoted}")

        if t.body:
            out.append("")
            _emit_entries(
                t.body,
                out,
                depth=0,
                kw_depth=0,
                max_depth=max_depth,
                threshold=threshold,
                show_timestamps=show_timestamps,
                show_timing=show_timing,
                full_paths=full_paths,
                output_dir=output_dir,
                highlight=highlight,
            )

    if data.execution_messages:
        out.append("")
        out.append(f"## Execution messages ({len(data.execution_messages)})")
        out.append("")
        for msg in data.execution_messages:
            # Execution messages are emitted unconditionally — they're
            # parser/discovery errors the user explicitly opted into with
            # `--execution-messages`, not filterable log output.
            _emit_message(
                msg,
                out,
                depth=0,
                threshold=0,
                show_timestamps=show_timestamps,
                full_paths=full_paths,
                output_dir=output_dir,
                highlight=highlight,
            )

    if data.extract_dir and data.extracted_count:
        out.append("")
        out.append(f"**Extracted:** {data.extracted_count} artefact(s) → `{data.extract_dir}`")

    if show_timing and (data.start_time or data.end_time or data.elapsed_seconds is not None):
        rows: List[List[str]] = []
        if data.start_time:
            rows.append(["Started", _fmt_timestamp(data.start_time)])
        if data.end_time:
            rows.append(["Ended", _fmt_timestamp(data.end_time)])
        if data.elapsed_seconds is not None:
            rows.append(["Elapsed", _fmt_elapsed(data.elapsed_seconds)])
        out.append("")
        out.append(_md_table(["Field", "Value"], rows, aligns=["left", "left"]))

    if data.filters_applied:
        out.append("")
        out.append(f"_Filters: {_md_escape(_format_filters(data.filters_applied))}_")

    return "\n".join(out) + "\n"


def _render_suite_header_md(suite: Optional[LogSuite], *, full_paths: bool) -> str:
    if suite is None:
        return ""
    head = f"## Suite: {_md_escape(suite.full_name)}"
    head += _path_paren(source=suite.source, rel_source=suite.rel_source, lineno=None, full_paths=full_paths)
    if suite.status:
        head += f" {_bold_status(suite.status)}"
    parts = [head]
    if suite.doc:
        for line in suite.doc.splitlines() or [suite.doc]:
            parts.append(f"> {_md_escape(line)}")
    if suite.metadata:
        parts.append("")
        for k, v in suite.metadata.items():
            parts.append(f"- **{_md_escape(k)}:** {_md_escape(v)}")
    return "\n".join(parts)


def _test_header_md(
    t: _TestLike,
    *,
    full_paths: bool,
    show_timing: bool,
    highlight: Optional[Callable[[str], str]] = None,
) -> str:
    name = _highlight_md(_md_escape(t.full_name), highlight)
    head = f"### Test: {name}"
    head += _source_paren(t, full_paths=full_paths)
    head += f" {_bold_status(t.status)}"
    head += _timing_suffix(t.elapsed_seconds, t.start_time, show_timing=show_timing)
    return head


def _emit_entries(
    entries: List[LogEntry],
    out: List[str],
    *,
    depth: int,
    kw_depth: int,
    max_depth: int,
    threshold: int,
    show_timestamps: bool,
    show_timing: bool,
    full_paths: bool,
    output_dir: Optional[Path] = None,
    highlight: Optional[Callable[[str], str]] = None,
) -> None:
    """Emit each entry as a markdown list item at the requested `depth`
    (children → `depth + 1`). MESSAGE entries become inline-code bullets,
    keywords/control-flow entries become bold-headed bullets with their
    body nested underneath."""
    for entry in entries:
        _emit_entry(
            entry,
            out,
            depth=depth,
            kw_depth=kw_depth,
            max_depth=max_depth,
            threshold=threshold,
            show_timestamps=show_timestamps,
            show_timing=show_timing,
            full_paths=full_paths,
            output_dir=output_dir,
            highlight=highlight,
        )


def _emit_entry(
    entry: LogEntry,
    out: List[str],
    *,
    depth: int,
    kw_depth: int,
    max_depth: int,
    threshold: int,
    show_timestamps: bool,
    show_timing: bool,
    full_paths: bool,
    output_dir: Optional[Path] = None,
    highlight: Optional[Callable[[str], str]] = None,
) -> None:
    if entry.type == "MESSAGE":
        _emit_message(
            entry,
            out,
            depth=depth,
            threshold=threshold,
            show_timestamps=show_timestamps,
            full_paths=full_paths,
            output_dir=output_dir,
            highlight=highlight,
        )
        return

    indent = "  " * depth
    cont = indent + "  "  # continuation column under the bullet's content
    etype = entry.type

    header = _entry_header_md(entry, show_timing=show_timing, highlight=highlight)
    out.append(f"{indent}- {header}")

    if etype in _KEYWORD_ENTRY_TYPES and (entry.doc or entry.tags or entry.timeout):
        _emit_keyword_info(entry, out, indent=cont, highlight=highlight)

    if entry.message and entry.status in ("FAIL", "SKIP"):
        for line in entry.message.splitlines() or [entry.message]:
            styled = _highlight_md(_md_escape(line), highlight)
            out.append(f"{cont}> {styled}")

    if not entry.body:
        return

    is_call = etype in _KEYWORD_ENTRY_TYPES
    new_kw_depth = kw_depth + 1 if is_call else kw_depth
    if is_call and max_depth > 0 and new_kw_depth >= max_depth:
        hidden = _count_hidden(entry.body)
        if hidden:
            out.append(f"{cont}- _… {hidden} hidden (`--max-depth {max_depth}`)_")
        return

    _emit_entries(
        entry.body,
        out,
        depth=depth + 1,
        kw_depth=new_kw_depth,
        max_depth=max_depth,
        threshold=threshold,
        show_timestamps=show_timestamps,
        show_timing=show_timing,
        full_paths=full_paths,
        output_dir=output_dir,
        highlight=highlight,
    )


def _emit_message(
    entry: LogEntry,
    out: List[str],
    *,
    depth: int,
    threshold: int,
    show_timestamps: bool,
    full_paths: bool,
    output_dir: Optional[Path] = None,
    highlight: Optional[Callable[[str], str]] = None,
) -> None:
    """A `MESSAGE` body item (log output / errors). Single-line messages
    become a one-liner ``- `[INFO] text` `` inline-code bullet; multi-line
    messages get a fenced code block under a bare-level bullet. Artefacts
    referenced by the message render as sub-bullets."""
    lvl = (entry.level or "INFO").upper()
    if _LEVEL_ORDER.get(lvl, 2) < threshold:
        return

    indent = "  " * depth
    cont = indent + "  "
    ts = f" [{entry.timestamp}]" if show_timestamps and entry.timestamp else ""
    text = entry.text or ""
    lines = text.splitlines() or [""]

    if len(lines) == 1 and "`" not in lines[0]:
        # Highlighted match is already wrapped in `…` so leave it alone;
        # otherwise wrap the whole `[LVL] text` in one inline-code span.
        rendered = _highlight_md(lines[0], highlight)
        if rendered == lines[0]:
            # No highlight match — wrap the whole line in one code span.
            out.append(f"{indent}- `[{lvl}]{ts} {lines[0]}`")
        else:
            # Highlight pieces are code-spans; place them next to a code-span
            # `[LVL]` badge to keep the structural look.
            out.append(f"{indent}- `[{lvl}]{ts}` {rendered}")
    else:
        # Multi-line OR contains backticks → fenced code block under a
        # short bullet that carries the level badge.
        out.append(f"{indent}- `[{lvl}]{ts}`")
        out.append(f"{cont}```")
        for line in lines:
            out.append(f"{cont}{line}")
        out.append(f"{cont}```")

    if entry.artifacts:
        _emit_artifacts(entry.artifacts, out, depth=depth + 1, full_paths=full_paths, output_dir=output_dir)


def _emit_keyword_info(
    entry: LogEntry,
    out: List[str],
    *,
    indent: str,
    highlight: Optional[Callable[[str], str]] = None,
) -> None:
    """Render the executed keyword's ``[Documentation]``/``[Tags]``/
    ``[Timeout]`` (`log --keyword-info`) as nested sub-bullets under the
    keyword's own bullet."""

    def _hi(s: str) -> str:
        return _highlight_md(_md_escape(s), highlight)

    if entry.doc:
        lines = entry.doc.splitlines() or [entry.doc]
        first, *rest = lines
        out.append(f"{indent}- **[Documentation]** {_hi(first)}")
        for line in rest:
            out.append(f"{indent}  {_hi(line)}")
    if entry.tags:
        out.append(f"{indent}- **[Tags]** " + " ".join(f"`{t}`" for t in entry.tags))
    if entry.timeout:
        out.append(f"{indent}- **[Timeout]** `{entry.timeout}`")


def _entry_header_md(
    entry: LogEntry,
    *,
    show_timing: bool = False,
    highlight: Optional[Callable[[str], str]] = None,
) -> str:
    """Markdown header for a non-MESSAGE entry. Keyword/control-flow type
    appears in bold; names with highlight applied inside the bold; args
    wrapped in inline-code spans. Status icon + bold status follows;
    timing tail in italics."""
    t = entry.type
    parts: List[str] = []

    def _name_md(name: str) -> str:
        """Bold keyword name with the search highlight applied inside."""
        return f"**{_highlight_md(_md_escape(name), highlight)}**"

    def _arg(text: str) -> str:
        """Inline-code-spanned argument value. Backticks inside the arg are
        rare but break the span; substitute the ASCII apostrophe so the
        span still renders cleanly."""
        sanitized = text.replace("`", "'")
        return f"`{sanitized}`"

    if t in ("KEYWORD", "SETUP", "TEARDOWN"):
        if t != "KEYWORD":
            parts.append(f"**[{t}]**")
        if entry.assign:
            parts.append(" ".join(_arg(a) for a in entry.assign) + " =")
        if entry.name:
            parts.append(_name_md(entry.name))
        if entry.args:
            parts.extend(_arg(a) for a in entry.args)
    elif t == "FOR":
        parts.append("**FOR**")
        if entry.assign:
            parts.extend(_arg(a) for a in entry.assign)
        if entry.flavor:
            parts.append(f"`{entry.flavor}`")
        if entry.args:
            parts.extend(_arg(a) for a in entry.args)
    elif t == "ITERATION":
        parts.append("**ITER**")
        if entry.assign:
            parts.extend(_arg(a) for a in entry.assign)
    elif t == "WHILE":
        parts.append("**WHILE**")
        if entry.condition:
            parts.append(_arg(entry.condition))
    elif t in ("IF", "ELSE IF"):
        parts.append(f"**{t}**")
        if entry.condition:
            parts.append(_arg(entry.condition))
    elif t == "ELSE":
        parts.append("**ELSE**")
    elif t == "TRY":
        parts.append("**TRY**")
    elif t == "EXCEPT":
        parts.append("**EXCEPT**")
        if entry.patterns:
            parts.extend(_arg(p) for p in entry.patterns)
        if entry.pattern_type:
            parts.append(f"_type={entry.pattern_type}_")
        if entry.assign:
            parts.append("AS")
            parts.extend(_arg(a) for a in entry.assign)
    elif t == "FINALLY":
        parts.append("**FINALLY**")
    elif t == "VAR":
        parts.append("**VAR**")
        if entry.assign:
            parts.append(_arg(entry.assign[0]))
        if entry.args:
            parts.extend(_arg(a) for a in entry.args)
        if entry.scope and entry.scope.upper() != "LOCAL":
            parts.append(f"_scope={entry.scope}_")
        if entry.separator is not None:
            parts.append(f"_separator={entry.separator!r}_")
    elif t == "RETURN":
        parts.append("**RETURN**")
        if entry.args:
            parts.extend(_arg(a) for a in entry.args)
    elif t in ("CONTINUE", "BREAK"):
        parts.append(f"**{t}**")
    elif t == "GROUP":
        parts.append("**GROUP**")
        if entry.name:
            parts.append(_name_md(entry.name))
    elif t == "ERROR":
        parts.append("**ERROR**")
        if entry.args:
            parts.extend(_arg(a) for a in entry.args)
    else:
        parts.append(f"**{t}**")
        if entry.name:
            parts.append(_name_md(entry.name))

    header = " ".join(parts)
    if entry.status and entry.status != "NOT SET":
        header += f" {_bold_status(entry.status)}"
    header += _timing_suffix(
        entry.elapsed_seconds,
        entry.start_time,
        show_timing=show_timing,
    )
    return header


def _count_hidden(entries: List[LogEntry]) -> int:
    total = 0
    for e in entries:
        total += 1
        if e.body:
            total += _count_hidden(e.body)
    return total


def _emit_artifacts(
    artefacts: List[ArtifactRef],
    out: List[str],
    *,
    depth: int,
    full_paths: bool = False,
    output_dir: Optional[Path] = None,
) -> None:
    """Render each artefact reference as a sub-bullet under its owning
    message. Images use ``![alt](url)`` so renderers that display images
    inline (GitHub, Slack) show them; other artefacts use ``[label](url)``
    so OSC-8-aware terminals make the path clickable. Embedded artefacts
    that haven't been extracted have no usable URL and fall back to a
    descriptive text line."""
    indent = "  " * depth
    for ref in artefacts:
        if ref.skipped_reason:
            out.append(f"{indent}- _(skipped {ref.kind} `{ref.src}`: {ref.skipped_reason})_")
            continue

        display = _artefact_display(ref, full_paths=full_paths, output_dir=output_dir)
        href = _artefact_href(ref, full_paths=full_paths, output_dir=output_dir)
        kind_label = "image" if ref.kind == "image" else "file"

        if href is None:
            # Embedded-but-not-extracted (no path on disk) or unresolved
            # external reference — neither has a URL we can link to.
            if ref.embedded:
                size = f", {_fmt_bytes(ref.approx_bytes)}" if ref.approx_bytes is not None else ""
                mt = f"{ref.media_type or ref.kind}{size}"
                out.append(f"{indent}- {kind_label}: _embedded {mt} — use `--extract` to save_")
            else:
                out.append(f"{indent}- {kind_label}: `{ref.src}` _(unresolved)_")
            continue

        # The link label is the visible path the user reads; for files
        # we show the (relative) path so the user knows *where* the
        # artefact lives, for images we show the file *name* alone so
        # the alt text doesn't repeat the URL.
        if ref.kind == "image":
            label = Path(display or ref.src or "image").name
            marker = "!"
        else:
            label = display or ref.src or kind_label
            marker = ""
        line = f"{indent}- {marker}[{label}]({href})"
        if ref.embedded and ref.approx_bytes is not None:
            mt = f"{ref.media_type or ref.kind}, {_fmt_bytes(ref.approx_bytes)}"
            line += f" _(extracted, {mt})_"
        out.append(line)


def _resolve_artefact_path(ref: ArtifactRef, *, output_dir: Optional[Path]) -> Optional[Path]:
    """Return the artefact's absolute filesystem path, or ``None`` when
    the artefact doesn't have one (embedded-not-extracted, or an
    unresolved external reference).

    ``ref.rel_path`` is stored relative to the *output.xml directory*,
    so we resolve it against ``output_dir`` to get an absolute path —
    that's the right anchor: the artefact lives next to (or near)
    output.xml on disk, not in the user's cwd.
    """
    if ref.extracted_to:
        return Path(ref.extracted_to)
    if ref.resolved_path:
        return Path(ref.resolved_path)
    if ref.rel_path and output_dir is not None:
        try:
            return (output_dir / ref.rel_path).resolve()
        except (ValueError, OSError):
            return None
    return None


def _artefact_display(ref: ArtifactRef, *, full_paths: bool, output_dir: Optional[Path] = None) -> str:
    """The visible label / display path for the artefact.

    ``full_paths=True`` returns the absolute path; otherwise we try to
    express the path relative to cwd (the natural anchor for stdout
    markdown). If the artefact lives outside cwd we fall back to the
    model's ``rel_path`` (relative to output.xml) when present, else
    the absolute path."""
    abs_path = _resolve_artefact_path(ref, output_dir=output_dir)
    if abs_path is None:
        return ref.src
    if full_paths:
        return str(abs_path)
    try:
        return abs_path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return ref.rel_path or str(abs_path)


def _artefact_href(ref: ArtifactRef, *, full_paths: bool = False, output_dir: Optional[Path] = None) -> Optional[str]:
    """Return a markdown link target for the artefact, or ``None`` when
    no file on disk is known (embedded-not-extracted, or unresolved).

    Default mode prefers a path relative to cwd — viewers that resolve
    relative paths against the markdown's location (GitHub, Slack with
    attached folder, the extract directory itself) can then display
    images and follow links. When the artefact lives outside cwd we
    fall back to an absolute ``file://`` URL so OSC 8 click-to-open
    still works in cooperating terminals.

    ``full_paths=True`` always returns the absolute ``file://`` URL,
    matching the rest of the renderer's ``--full-paths`` behaviour.
    """
    abs_path = _resolve_artefact_path(ref, output_dir=output_dir)
    if abs_path is None:
        return None
    try:
        if full_paths:
            return abs_path.as_uri()
        try:
            return abs_path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            return abs_path.as_uri()
    except (ValueError, OSError):
        return None
