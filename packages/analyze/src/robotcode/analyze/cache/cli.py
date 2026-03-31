from pathlib import Path
from typing import Optional, Tuple

import click

from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.utils import get_config_files
from robotcode.robot.diagnostics.data_cache import CACHE_DIR_NAME, CacheSection, SqliteDataCache, build_cache_dir

from ..config import AnalyzeConfig

_SECTION_NAMES = {s.name.lower(): s for s in CacheSection}


def _resolve_cache(
    app: Application,
    paths: Tuple[Path, ...],
) -> Tuple[Path, Optional[SqliteDataCache]]:
    config_files, root_folder, _ = get_config_files(
        paths,
        app.config.config_files,
        root_folder=app.config.root,
        no_vcs=app.config.no_vcs,
        verbose_callback=app.verbose,
    )

    robot_config = load_robot_config_from_path(
        *config_files, extra_tools={"robotcode-analyze": AnalyzeConfig}, verbose_callback=app.verbose
    )

    analyzer_config = robot_config.tool.get("robotcode-analyze", None) if robot_config.tool is not None else None

    cache_base_path = root_folder or Path.cwd()
    if analyzer_config is not None and isinstance(analyzer_config, AnalyzeConfig):
        if analyzer_config.cache is not None and analyzer_config.cache.cache_dir is not None:
            cache_base_path = Path(analyzer_config.cache.cache_dir)

    cache_dir = build_cache_dir(cache_base_path)

    if not cache_dir.exists() or not (cache_dir / "cache.db").exists():
        return cache_dir, None

    from ..__version__ import __version__

    return cache_dir, SqliteDataCache(cache_dir, app_version=__version__)


def _parse_sections(sections: Tuple[str, ...]) -> Optional[Tuple[CacheSection, ...]]:
    if not sections:
        return None

    result = []
    for s in sections:
        s_lower = s.lower()
        if s_lower not in _SECTION_NAMES:
            raise click.BadParameter(
                f"Unknown section '{s}'. Choose from: {', '.join(_SECTION_NAMES)}",
                param_hint="'--section'",
            )
        result.append(_SECTION_NAMES[s_lower])
    return tuple(result)


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


@click.group(
    name="cache",
    add_help_option=True,
    invoke_without_command=False,
)
def cache_group() -> None:
    """\
    Manage the RobotCode analysis cache.

    Provides subcommands to inspect, list, and clear cached data
    (library docs, variables, resources, namespaces).
    """


@cache_group.command(name="path")
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True, path_type=Path)
)
@pass_application
def cache_path(app: Application, paths: Tuple[Path, ...]) -> None:
    """\
    Print the cache directory path.

    Outputs the resolved cache directory for the current project
    and Python/Robot Framework version combination.
    """
    cache_dir, db = _resolve_cache(app, paths)
    try:
        app.echo(str(cache_dir))
    finally:
        if db is not None:
            db.close()


@cache_group.command(name="info")
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True, path_type=Path)
)
@pass_application
def cache_info(app: Application, paths: Tuple[Path, ...]) -> None:
    """\
    Show cache statistics.

    Displays the cache directory, database size, app version, and
    per-section entry counts with timestamps.
    """
    cache_dir, db = _resolve_cache(app, paths)

    if db is None:
        app.echo(f"Cache directory: {cache_dir}")
        app.echo("No cache database found.")
        return

    try:
        db_path = db.db_path
        db_size = db_path.stat().st_size if db_path.exists() else 0

        section_data = []
        total_entries = 0
        total_bytes = 0
        for section in CacheSection:
            stats = db.get_section_stats(section)
            total_entries += stats.entry_count
            total_bytes += stats.total_blob_bytes
            section_data.append(
                {
                    "section": section.name.lower(),
                    "entries": stats.entry_count,
                    "size": stats.total_blob_bytes,
                    "size_formatted": _format_bytes(stats.total_blob_bytes) if stats.entry_count else "—",
                    "created": stats.oldest_created or None,
                    "modified": stats.newest_modified or None,
                }
            )

        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            if app.colored:
                lines = [
                    f"- **Directory:** {cache_dir}",
                    f"- **Database:** {db_path.name} ({_format_bytes(db_size)})",
                    f"- **Version:** {db.app_version or '(unknown)'}",
                    "",
                    "| Section | Entries | Size | Created | Modified |",
                    "|---|---:|---:|---|---|",
                ]
                for s in section_data:
                    lines.append(
                        f"| {s['section']} | {s['entries']} | {s['size_formatted']}"
                        f" | {s['created'] or '—'} | {s['modified'] or '—'} |"
                    )
                lines.append(f"| **Total** | **{total_entries}** | **{_format_bytes(total_bytes)}** | | |")
                app.echo_as_markdown("\n".join(lines))
            else:
                app.echo(f"  Directory:  {cache_dir}")
                app.echo(f"  Database:   {db_path.name}  ({_format_bytes(db_size)})")
                app.echo(f"  Version:    {db.app_version or '(unknown)'}")
                app.echo("")
                header = f"  {'Section':<12} {'Entries':>7}  {'Size':>10}  {'Created':19}  {'Modified':19}"
                app.echo(header)
                app.echo(f"  {'─' * (len(header) - 2)}")
                for s in section_data:
                    app.echo(
                        f"  {s['section']:<12} {s['entries']:>7}  {s['size_formatted']:>10}"
                        f"  {(s['created'] or '—'):19}  {(s['modified'] or '—'):19}"
                    )
                app.echo(f"  {'─' * (len(header) - 2)}")
                app.echo(f"  {'Total':<12} {total_entries:>7}  {_format_bytes(total_bytes):>10}")
        else:
            app.print_data(
                {
                    "directory": str(cache_dir),
                    "database": db_path.name,
                    "database_size": db_size,
                    "version": db.app_version or "",
                    "sections": [
                        {k: v for k, v in s.items() if k != "size_formatted" and v is not None} for s in section_data
                    ],
                    "total_entries": total_entries,
                    "total_size": total_bytes,
                }
            )
    finally:
        db.close()


@cache_group.command(name="list")
@click.option(
    "-s",
    "--section",
    "sections",
    multiple=True,
    metavar="SECTION",
    help="Filter by section (library, variables, resource, namespace). Can be specified multiple times.",
)
@click.option(
    "-p",
    "--pattern",
    "patterns",
    multiple=True,
    metavar="PATTERN",
    help="Filter entries by glob pattern (e.g. 'robot.*', '*BuiltIn*'). Can be specified multiple times.",
)
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True, path_type=Path)
)
@pass_application
def cache_list(app: Application, sections: Tuple[str, ...], patterns: Tuple[str, ...], paths: Tuple[Path, ...]) -> None:
    """\
    List cached entries.

    Shows all entries in the cache with their timestamps and sizes.
    Use --section to filter by specific cache sections.
    Use --pattern to filter entries by glob pattern.
    """
    from fnmatch import fnmatch

    _, db = _resolve_cache(app, paths)

    if db is None:
        app.echo("No cache database found.")
        return

    try:
        selected = _parse_sections(sections)
        target_sections = selected if selected else tuple(CacheSection)

        def _matches(name: str) -> bool:
            if not patterns:
                return True
            return any(fnmatch(name, p) for p in patterns)

        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            if app.colored:
                lines: list[str] = []
                for section in target_sections:
                    entries = [e for e in db.list_entries(section) if _matches(e.entry_name)]
                    if not entries:
                        continue
                    lines.append(f"### {section.name.lower()} ({len(entries)} entries)")
                    lines.append("")
                    lines.append("| Name | Size | Created | Modified |")
                    lines.append("|---|---:|---|---|")
                    for entry in entries:
                        size = _format_bytes(entry.meta_bytes + entry.data_bytes)
                        created = entry.created_at or "—"
                        modified = entry.modified_at or "—"
                        lines.append(f"| {entry.entry_name} | {size} | {created} | {modified} |")
                    lines.append("")
                if lines:
                    app.echo_as_markdown("\n".join(lines))
                else:
                    app.echo("No entries found.")
            else:
                found = False
                for section in target_sections:
                    entries = [e for e in db.list_entries(section) if _matches(e.entry_name)]
                    if not entries:
                        continue
                    found = True
                    app.echo(f"[{section.name.lower()}] ({len(entries)} entries)")
                    for entry in entries:
                        size = _format_bytes(entry.meta_bytes + entry.data_bytes)
                        created = entry.created_at or "—"
                        modified = entry.modified_at or "—"
                        app.echo(f"  {entry.entry_name}  size={size}  created={created}  modified={modified}")
                    app.echo("")
                if not found:
                    app.echo("No entries found.")
        else:
            result: dict[str, list[dict[str, object]]] = {}
            for section in target_sections:
                entries = [e for e in db.list_entries(section) if _matches(e.entry_name)]
                if entries:
                    result[section.name.lower()] = [
                        {
                            k: v
                            for k, v in {
                                "name": e.entry_name,
                                "size": e.meta_bytes + e.data_bytes,
                                "created": e.created_at,
                                "modified": e.modified_at,
                            }.items()
                            if v is not None
                        }
                        for e in entries
                    ]
            app.print_data(result)
    finally:
        db.close()


@cache_group.command(name="clear")
@click.option(
    "-s",
    "--section",
    "sections",
    multiple=True,
    metavar="SECTION",
    help="Clear only specific sections (library, variables, resource, namespace). Can be specified multiple times.",
)
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True, path_type=Path)
)
@pass_application
def cache_clear(app: Application, sections: Tuple[str, ...], paths: Tuple[Path, ...]) -> None:
    """\
    Clear the analysis cache.

    Removes cached entries from the database. By default clears all sections.
    Use --section to clear specific sections only.
    """
    _, db = _resolve_cache(app, paths)

    if db is None:
        app.echo("No cache database found.")
        return

    try:
        selected = _parse_sections(sections)

        if selected:
            total = 0
            for section in selected:
                count = db.clear_section(section)
                total += count
                app.echo(f"Cleared {count} entries from {section.name.lower()}.")
        else:
            total = db.clear_all()

        app.echo(f"Removed {total} entries total.")
    finally:
        db.close()


def _resolve_cache_root(
    app: Application,
    paths: Tuple[Path, ...],
) -> Path:
    config_files, root_folder, _ = get_config_files(
        paths,
        app.config.config_files,
        root_folder=app.config.root,
        no_vcs=app.config.no_vcs,
        verbose_callback=app.verbose,
    )

    robot_config = load_robot_config_from_path(
        *config_files, extra_tools={"robotcode-analyze": AnalyzeConfig}, verbose_callback=app.verbose
    )

    analyzer_config = robot_config.tool.get("robotcode-analyze", None) if robot_config.tool is not None else None

    cache_base_path = root_folder or Path.cwd()
    if analyzer_config is not None and isinstance(analyzer_config, AnalyzeConfig):
        if analyzer_config.cache is not None and analyzer_config.cache.cache_dir is not None:
            cache_base_path = Path(analyzer_config.cache.cache_dir)

    return cache_base_path / CACHE_DIR_NAME


@cache_group.command(name="prune")
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True, path_type=Path)
)
@pass_application
def cache_prune(app: Application, paths: Tuple[Path, ...]) -> None:
    """\
    Remove the entire cache directory.

    Deletes the .robotcode_cache directory and all its contents,
    including caches for all Python and Robot Framework versions.
    """
    import shutil

    cache_root = _resolve_cache_root(app, paths)

    if not cache_root.exists():
        app.echo(f"Cache directory does not exist: {cache_root}")
        return

    shutil.rmtree(cache_root)
    app.echo(f"Removed {cache_root}")
