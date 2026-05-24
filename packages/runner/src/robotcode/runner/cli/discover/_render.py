"""Markdown renderers for `robotcode discover` TEXT-mode output.

Each `render_*` returns a single markdown string. The caller pipes it
through `app.echo_as_markdown(...)`, which decides between rich-themed
ANSI on a coloured TTY and raw markdown on a pipe / `--no-color`.

Style conventions (shared with `results`):

- **bold** for entities (test/suite/tag names),
- *italic* for labels (Tags, Total, Statistics block field names go in
  a table heading instead),
- `` `code` `` for file paths and `path:line` references (the
  `path_paren` helper from `cli/_markdown` handles this uniformly).
"""

from dataclasses import fields
from typing import Callable, Dict, Iterable, List, Optional

from .._markdown import (
    field_list_md,
    filters_footer_md,
    highlight_md,
    md_escape,
    path_paren,
)
from ._models import Info, Statistics, TestItem

# Convert `Info` field names to friendly labels for the field/value table.
# Unmapped keys fall through to a title-cased version of the snake_case
# name so additions to `Info` keep rendering without a code change.
_INFO_LABELS: Dict[str, str] = {
    "robot_version_string": "Robot Framework",
    "robot_env": "Robot Environment",
    "robotcode_version_string": "RobotCode",
    "python_version_string": "Python",
    "executable": "Executable",
    "machine": "Machine",
    "processor": "Processor",
    "platform": "Platform",
    "system": "System",
    "system_version": "System Version",
}

# Stats field order — fixed across all subcommands so tables line up.
_STATS_FIELDS = [
    ("suites", "Suites"),
    ("suites_with_tests", "Suites with tests"),
    ("suites_with_tasks", "Suites with tasks"),
    ("tests", "Tests"),
    ("tasks", "Tasks"),
]


def _item_lineno(item: TestItem) -> Optional[int]:
    """Test/task items carry their line number on `range.start.line`
    (0-indexed); 1-based for display. Returns `None` for items without
    a meaningful line (suites, workspace)."""
    if item.range is not None:
        return item.range.start.line + 1
    return item.lineno


def _item_paren(item: TestItem, *, full_paths: bool, with_line: bool) -> str:
    """`(`path:line`)` for tests / tasks, `(`path`)` for suites."""
    return path_paren(
        source=item.source,
        rel_source=item.rel_source,
        lineno=_item_lineno(item) if with_line else None,
        full_paths=full_paths,
    )


def _hi(text: str, highlight: Optional[Callable[[str], str]]) -> str:
    return highlight_md(md_escape(text), highlight)


def _search_filters_dict(search_substring: Optional[str], search_regex: Optional[str]) -> Dict[str, List[str]]:
    """Build the discover-shaped filters dict (only `search` /
    `search-regex` are exposed; tag/include/etc. are passed straight
    through to Robot's discovery and never show in the footer)."""
    filters: Dict[str, List[str]] = {}
    if search_substring:
        filters["search"] = [search_substring]
    if search_regex:
        filters["search-regex"] = [search_regex]
    return filters


def _block_md(
    *,
    heading: str,
    body_md: str,
    statistics: Statistics,
    search_substring: Optional[str] = None,
    search_regex: Optional[str] = None,
) -> str:
    """Standard discover-renderer shape: H1 heading, body content,
    `## Statistics` block, optional filters footer. Pull the per-
    subcommand variation into the caller's `body_md` (a pre-rendered
    markdown string)."""
    parts = [f"# {heading}", "", body_md, "", render_statistics_md(statistics)]
    footer = filters_footer_md(_search_filters_dict(search_substring, search_regex))
    if footer:
        parts.append("")
        parts.append(footer)
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Statistics block — common footer for `all`, `tests`, `tasks`, `suites`,
# `tags`. Same shape as the `## Statistics` block in `results`.
# ---------------------------------------------------------------------------


def render_statistics_md(statistics: Statistics) -> str:
    rows: List[List[str]] = []
    for attr, label in _STATS_FIELDS:
        value = getattr(statistics, attr, 0)
        # Match the old behaviour: total `suites` always rendered, the
        # rest only when non-zero (their `format_statistics` counterpart
        # skipped zero rows).
        if attr == "suites" or value:
            rows.append([label, str(value)])
    return "## Statistics\n\n" + field_list_md(rows)


# ---------------------------------------------------------------------------
# `discover info`
# ---------------------------------------------------------------------------


def render_info(info: Info) -> str:
    """Render the environment-info dataclass as an italic-label bullet
    list.

    Iterates the actual dataclass fields (preserving definition order)
    so a new field on `Info` shows up automatically with a sensible
    title-cased label. Curated labels in `_INFO_LABELS` are used when
    present; falsy values are dropped to match the old
    `as_dict(info, remove_defaults=True)` behaviour."""
    rows: List[List[str]] = []
    for f in fields(info):
        value = getattr(info, f.name)
        if not value:
            continue
        label = _INFO_LABELS.get(f.name) or f.name.replace("_", " ").title()
        rows.append([label, str(value)])

    parts = ["# Info", "", field_list_md(rows, empty_text="_(no fields)_")]
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# `discover files`
# ---------------------------------------------------------------------------


def render_files(paths: List[str]) -> str:
    """Bullet list of file paths, with a `_Total:_` count footer.

    Paths are wrapped in inline-code spans (`` `tests/foo.robot` ``)
    consistent with the `(`path:line`)` form everywhere else.
    Per-match search highlighting isn't applied: backtick wrapping
    inside the surrounding code span would break it, and `--search`
    already filters the list itself, so the user only sees matching
    paths anyway."""
    parts = ["# Files", ""]
    if not paths:
        parts.append("_(no files matched)_")
        return "\n".join(parts) + "\n"

    for p in paths:
        # Backticks inside a path are vanishingly rare; if they happen,
        # the inline-code span would break — strip them defensively the
        # same way `_arg` does in the log renderer.
        safe = p.replace("`", "'")
        parts.append(f"- `{safe}`")

    parts.append("")
    parts.append(f"_Total:_ {len(paths)} file(s)")
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# `discover suites`
# ---------------------------------------------------------------------------


def render_suites(
    suites: List[TestItem],
    statistics: Statistics,
    *,
    full_paths: bool,
    highlight: Optional[Callable[[str], str]] = None,
    search_substring: Optional[str] = None,
    search_regex: Optional[str] = None,
) -> str:
    if not suites:
        body_md = "_(no suites matched)_"
    else:
        body_md = "\n".join(
            f"- **{_hi(s.longname, highlight)}**{_item_paren(s, full_paths=full_paths, with_line=False)}"
            for s in suites
        )
    return _block_md(
        heading="Suites",
        body_md=body_md,
        statistics=statistics,
        search_substring=search_substring,
        search_regex=search_regex,
    )


# ---------------------------------------------------------------------------
# `discover tests` / `discover tasks` — flat list filtered by type
# ---------------------------------------------------------------------------


def render_tests_or_tasks(
    items: Iterable[TestItem],
    statistics: Statistics,
    *,
    selected_type: str,
    show_tags: bool,
    full_paths: bool,
    highlight: Optional[Callable[[str], str]] = None,
    search_substring: Optional[str] = None,
    search_regex: Optional[str] = None,
) -> str:
    """Render the flat list of `tests` or `tasks` (`selected_type`
    drives both the heading and the filter)."""
    heading = "Tests" if selected_type == "test" else "Tasks"
    filtered = [it for it in items if it.type == selected_type]

    if not filtered:
        body_md = f"_(no {selected_type}s matched)_"
    else:
        lines: List[str] = []
        for item in filtered:
            name = _hi(item.longname, highlight)
            paren = _item_paren(item, full_paths=full_paths, with_line=True)
            lines.append(f"- **{name}**{paren}")
            if show_tags and item.tags:
                tags = ", ".join(f"`{_hi(str(tag), highlight)}`" for tag in sorted(item.tags))
                lines.append(f"  - _Tags:_ {tags}")
        body_md = "\n".join(lines)

    return _block_md(
        heading=heading,
        body_md=body_md,
        statistics=statistics,
        search_substring=search_substring,
        search_regex=search_regex,
    )


# ---------------------------------------------------------------------------
# `discover tags`
# ---------------------------------------------------------------------------


def render_tags(
    tags: Dict[str, List[TestItem]],
    statistics: Statistics,
    *,
    show_tests: bool,
    show_tasks: bool,
    full_paths: bool,
    highlight: Optional[Callable[[str], str]] = None,
    search_substring: Optional[str] = None,
    search_regex: Optional[str] = None,
) -> str:
    if not tags:
        body_md = "_(no tags matched)_"
    else:
        lines: List[str] = []
        for tag, items in sorted(tags.items()):
            lines.append(f"- **{_hi(tag, highlight)}**")
            if not (show_tests or show_tasks):
                continue
            for t in items:
                if show_tests != show_tasks:
                    if show_tests and t.type != "test":
                        continue
                    if show_tasks and t.type != "task":
                        continue
                name = _hi(t.longname, highlight)
                paren = _item_paren(t, full_paths=full_paths, with_line=True)
                lines.append(f"  - **{name}**{paren}")
        body_md = "\n".join(lines)

    return _block_md(
        heading="Tags",
        body_md=body_md,
        statistics=statistics,
        search_substring=search_substring,
        search_regex=search_regex,
    )


# ---------------------------------------------------------------------------
# `discover all` — workspace → suites → tests/tasks tree as nested list
# ---------------------------------------------------------------------------


def render_all(
    root: TestItem,
    statistics: Statistics,
    *,
    show_tags: bool,
    full_paths: bool,
    highlight: Optional[Callable[[str], str]] = None,
    search_substring: Optional[str] = None,
    search_regex: Optional[str] = None,
) -> str:
    """The full discovery tree: workspace at depth 0, suites at
    increasing depth, tests/tasks as leaves with their line number."""
    tree_lines: List[str] = []
    _emit_tree(root, tree_lines, depth=0, show_tags=show_tags, full_paths=full_paths, highlight=highlight)
    return _block_md(
        heading="All",
        body_md="\n".join(tree_lines),
        statistics=statistics,
        search_substring=search_substring,
        search_regex=search_regex,
    )


def _emit_tree(
    item: TestItem,
    out: List[str],
    *,
    depth: int,
    show_tags: bool,
    full_paths: bool,
    highlight: Optional[Callable[[str], str]] = None,
) -> None:
    indent = "  " * depth
    name = _hi(item.longname, highlight)
    is_leaf = item.type in ("test", "task")
    paren = _item_paren(item, full_paths=full_paths, with_line=is_leaf)
    out.append(f"{indent}- **{name}**{paren}")
    if is_leaf and show_tags and item.tags:
        tags = ", ".join(f"`{_hi(str(tag), highlight)}`" for tag in sorted(item.tags))
        out.append(f"{indent}  - _Tags:_ {tags}")
    for child in item.children or []:
        _emit_tree(child, out, depth=depth + 1, show_tags=show_tags, full_paths=full_paths, highlight=highlight)
