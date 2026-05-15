"""Acceptance tests for `robotcode discover tasks`."""

from pathlib import Path
from typing import Any

from .conftest import CliRunner, JsonRunner


def _names(items: list[Any]) -> set[str]:
    return {i["name"] for i in items}


def test_tasks_returns_only_tasks(json_discover: JsonRunner, tasks_suite: Path) -> None:
    """A pure `*** Tasks ***` file produces type="task" items."""
    data = json_discover("tasks", suite_path=tasks_suite)
    assert _names(data["items"]) == {"Process Invoices", "Sync Inventory", "Notify Stakeholders"}
    assert all(item["type"] == "task" for item in data["items"])


def test_tasks_in_mixed_dir_returns_only_tasks(json_discover: JsonRunner, mixed_suite: Path) -> None:
    """Mixed workspace: `tasks` returns only the items from the Tasks file."""
    data = json_discover("tasks", suite_path=mixed_suite)
    assert _names(data["items"]) == {"Task One", "Task Two"}


def test_tasks_empty_on_tests_only_suite(json_discover: JsonRunner, flat_suite: Path) -> None:
    """flat.robot has only Tests; `tasks` returns an empty list."""
    data = json_discover("tasks", suite_path=flat_suite)
    assert data["items"] == []


def test_tasks_tags_in_json(json_discover: JsonRunner, tasks_suite: Path) -> None:
    data = json_discover("tasks", suite_path=tasks_suite)
    tagged = [t for t in data["items"] if t.get("tags")]
    # tasks.robot tags every task; all three are tagged.
    assert len(tagged) == len(data["items"])


def test_tasks_include_filter(json_discover: JsonRunner, tasks_suite: Path) -> None:
    data = json_discover("tasks", "--include", "rpa", suite_path=tasks_suite)
    assert _names(data["items"]) == {"Process Invoices", "Sync Inventory"}


def test_tasks_text_full_paths(robotcode_cli: CliRunner, tasks_suite: Path) -> None:
    abs_str = str(tasks_suite.resolve())
    full = robotcode_cli(["--root", str(tasks_suite.parent), "discover", "tasks", "--full-paths", str(tasks_suite)])
    short = robotcode_cli(["--root", str(tasks_suite.parent), "discover", "tasks", str(tasks_suite)])
    assert abs_str in full.stdout
    assert abs_str not in short.stdout
