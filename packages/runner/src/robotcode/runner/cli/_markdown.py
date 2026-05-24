"""Markdown rendering helpers shared by `robotcode` CLI subcommands.

Every CLI command that emits human-readable TEXT output (`results`,
`discover`, …) routes through `app.echo_as_markdown(...)`:

- on a coloured TTY, `rich` renders the markdown to themed ANSI and
  pages if needed,
- in a pipe (or with `--no-color`), the raw markdown is emitted
  verbatim — pipe-friendly, LLM-friendly, pastable.

These helpers are the building blocks: escape rules, table layout,
status badges with display-width-aware padding, path/line references
wrapped as inline code, search highlighters that mark matches with
inline-code spans, and the small set of time/elapsed formatters that
recur across renderers.

Style conventions (kept consistent across commands):

- **bold** is reserved for *entities*: test names, suite names, tag
  names, status words (`**FAIL**`).
- *italic* marks *labels* / metadata: `_Tags:_`, `_Total:_`,
  `_Started:_`, `_Extracted:_`, user-defined metadata keys.
- `` `code` `` spans wrap file paths and `path:line` references,
  argument values, and search matches — code tokens, not prose.
"""

import re
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Time / size formatters
# ---------------------------------------------------------------------------


def fmt_elapsed(seconds: Optional[float]) -> str:
    if seconds is None:
        return "n/a"
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    minutes, sec = divmod(seconds, 60)
    return f"{int(minutes)} min {sec:.1f} s"


def fmt_timestamp(iso: Optional[str]) -> str:
    """ISO 8601 timestamp rendered as `YYYY-MM-DD HH:MM:SS`."""
    if not iso:
        return ""
    try:
        from datetime import datetime

        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return iso


def fmt_time_only(iso: Optional[str]) -> str:
    """Only the `HH:MM:SS` part of an ISO 8601 timestamp."""
    if not iso:
        return ""
    try:
        from datetime import datetime

        return datetime.fromisoformat(iso).strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return iso


def fmt_bytes(n: int) -> str:
    for unit in ("B", "kB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n = int(n / 1024)
    return f"{n:.1f} TB"


def format_filters(filters: Dict[str, List[str]]) -> str:
    """Render an applied-filter dict as `key=v1, v2; key2=v3`."""
    return "; ".join(f"{k}={', '.join(v)}" for k, v in filters.items() if v)


def filters_footer_md(filters: Optional[Dict[str, List[str]]]) -> Optional[str]:
    """Render the standard ``_Filters: key=v1, v2; …_`` footer line, or
    ``None`` when no filters are applied. Returning `None` lets the
    caller skip the surrounding blank-line padding."""
    if not filters or not any(v for v in filters.values()):
        return None
    return f"_Filters: {md_escape(format_filters(filters))}_"


# ---------------------------------------------------------------------------
# Markdown text helpers
# ---------------------------------------------------------------------------


# Characters that have markdown meaning anywhere in a line — escape them
# in arbitrary user content (test names, tags, messages). We deliberately
# leave alone:
# - `#`, `+`, `-`, `!`: only special at the start of a line, and the
#   renderer never places user data there.
# - `|`: escaped separately by `md_pipe` (only matters inside tables).
# - `_`: CommonMark disables intraword underscore emphasis, so identifiers
#   like `KW_DOC_TOKEN_beta` or `${var_name}` stay literal without escapes.
MD_ESCAPE_RE = re.compile(r"([\\`*\[\]])")


def md_escape(text: str) -> str:
    """Escape markdown metacharacters in arbitrary user content (test
    names, tags, paths). Safe to apply even when the content has no
    specials."""
    return MD_ESCAPE_RE.sub(r"\\\1", text)


def md_pipe(text: str) -> str:
    """Escape only the table-cell separator for use inside markdown tables."""
    return text.replace("|", "\\|")


def path_paren(
    *,
    source: Optional[str],
    rel_source: Optional[str],
    lineno: Optional[int],
    full_paths: bool,
) -> str:
    """Trailing `` (`path:line`) `` suffix (or `` (`path`) `` when
    `lineno` is `None`) — VS Code's terminal link detector picks up the
    `path:line` string inside the code span. Empty string when no path
    is available."""
    path = source if full_paths else (rel_source or source)
    if not path:
        return ""
    if lineno is None:
        return f" (`{path}`)"
    return f" (`{path}:{lineno}`)"


def timing_suffix(
    elapsed_seconds: Optional[float],
    start_time: Optional[str],
    *,
    show_timing: bool,
) -> str:
    """Italic `` _(13:34:23 · 12 ms)_ `` suffix or an empty string."""
    parts: List[str] = []
    if show_timing and start_time:
        parts.append(fmt_time_only(start_time))
    if elapsed_seconds is not None:
        parts.append(fmt_elapsed(elapsed_seconds))
    if not parts:
        return ""
    return f" _({' · '.join(parts)})_"


# ---------------------------------------------------------------------------
# Status icons + bold word
# ---------------------------------------------------------------------------


STATUS_ICONS = {
    "PASS": "✅",
    "FAIL": "❌",
    "SKIP": "⏭",
    "NOT RUN": "⏸",
    "NOT SET": "⚪",
}


# Display-width adjustment for the (small, fixed) emoji set the renderer
# emits. Most emoji codepoints render as two terminal cells but `len()`
# counts them as one — so naive padding under-pads any row containing an
# emoji. We explicitly track the icons we use rather than a regex range,
# because the misc-technical block (U+2300..U+23FF) holds both
# double-width emoji (`⏭`, `⏸`) and single-width geometric shapes —
# a range-based heuristic would either miss our icons or misclassify
# unrelated content.
DOUBLE_WIDTH_ICONS: "frozenset[str]" = frozenset(STATUS_ICONS.values())


def status_icon(status: str) -> str:
    return STATUS_ICONS.get(status.upper(), "")


def bold_status(status: str, *, icon: bool = True) -> str:
    """Icon + bold status word: ``❌ **FAIL**``. The icon gives a scanable
    visual marker for terminal / Slack / GitHub paste; the bold word keeps
    the status readable for screen readers and stays meaningful in
    rendering targets that don't paint emoji. Pass ``icon=False`` to
    suppress the emoji (e.g. when the cell is followed by a separator or
    you want to stay strictly ASCII)."""
    word = f"**{status.upper()}**"
    if icon:
        ic = status_icon(status)
        if ic:
            return f"{ic} {word}"
    return word


def display_width(text: str) -> int:
    """Source length plus one extra column per known double-width emoji."""
    return len(text) + sum(1 for ch in text if ch in DOUBLE_WIDTH_ICONS)


# ---------------------------------------------------------------------------
# Field/value bullet list — replaces 2-column markdown tables where a
# generic "Field | Value" header would just be noise (info blocks,
# statistics counts, summary metrics). The label gets the italic-label
# treatment (`_label:_`) consistent with the project-wide convention;
# the value is passed through verbatim so callers can include bold
# status words, inline-code paths, etc.
# ---------------------------------------------------------------------------


def field_list_md(rows: List[List[str]], *, empty_text: str = "") -> str:
    """Render `[[label, value], …]` as ``- _label:_ value`` bullets.

    Returns ``empty_text`` (default: empty string) when ``rows`` is
    empty — pass ``empty_text="_(none)_"`` or similar for an explicit
    placeholder."""
    if not rows:
        return empty_text
    return "\n".join(f"- _{label}:_ {value}" for label, value in rows)


# ---------------------------------------------------------------------------
# Markdown table with display-width-aware column padding
# ---------------------------------------------------------------------------


def md_table(headers: List[str], rows: List[List[str]], *, aligns: Optional[List[str]] = None) -> str:
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

    escaped_rows = [[md_pipe(cell) for cell in r] for r in rows]
    # Per-column visual width = max(header, all cells). Display-width-aware
    # so emoji cells (counted as 2 terminal columns) don't under-pad the
    # column. Floor at 3 so the `---` separator stays valid for narrow
    # columns like a one-digit count.
    widths: List[int] = []
    for col, header in enumerate(headers):
        w = display_width(header)
        for r in escaped_rows:
            if col < len(r):
                w = max(w, display_width(r[col]))
        widths.append(max(w, 3))

    def _pad(text: str, width: int, align: str) -> str:
        extra = width - display_width(text)
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


# ---------------------------------------------------------------------------
# Search-match highlighter (inline-code span around each match)
# ---------------------------------------------------------------------------


def highlight_md(text: str, highlight: Optional[Callable[[str], str]]) -> str:
    """Apply the search-highlight callback if any; the renderer wraps
    matches in inline-code spans (`` `match` ``) — visually distinct in
    rich, portable in raw markdown."""
    return highlight(text) if highlight else text


def make_md_highlighter(search_substring: Optional[str], search_regex: Optional[str]) -> Optional[Callable[[str], str]]:
    """Build a `text -> highlighted text` callback that wraps each
    regex/substring match in an inline-code span. Returns `None` when
    no pattern is supplied or the pattern fails to compile."""
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
