"""Helpers shared across the `robotcode results` acceptance tests."""

import re
from typing import Any, Dict, Iterator, List, Optional

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences so text output can be asserted on."""
    return _ANSI_RE.sub("", s)


def find_test(tests: List[Dict[str, Any]], full_name: str) -> Optional[Dict[str, Any]]:
    """Locate a test entry inside a `ShowResult` / `LogResult` `tests` list."""
    for t in tests:
        if t.get("fullName") == full_name or t.get("full_name") == full_name:
            return t
    return None


def iter_body(body: Optional[List[Dict[str, Any]]]) -> Iterator[Dict[str, Any]]:
    """Recursively walk a `LogEntry.body` tree (depth-first)."""
    if not body:
        return
    for entry in body:
        yield entry
        yield from iter_body(entry.get("body"))


def count_entries_of_type(body: Optional[List[Dict[str, Any]]], type_name: str) -> int:
    return sum(1 for e in iter_body(body) if e.get("type") == type_name)


def assert_counts(
    counts: Dict[str, Any],
    *,
    total: Optional[int] = None,
    passed: Optional[int] = None,
    failed: Optional[int] = None,
    skipped: Optional[int] = None,
    not_run: Optional[int] = None,
) -> None:
    """Assert the four-or-five count fields of a `Counts` dict."""
    expectations: Dict[str, Optional[int]] = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }
    if not_run is not None:
        expectations["notRun"] = not_run
    for key, expected in expectations.items():
        if expected is None:
            continue
        # Tolerate both camel and snake field names — Click/Mashumaro is camelCase by default.
        actual = counts.get(key, counts.get(_camel_to_snake(key)))
        assert actual == expected, f"counts.{key}: expected {expected}, got {actual} (full: {counts})"


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def get_field(d: Dict[str, Any], *names: str, default: Any = None) -> Any:
    """Fetch a field tolerating both camelCase and snake_case keys."""
    for n in names:
        if n in d:
            return d[n]
    return default
