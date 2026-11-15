"""Acceptance tests for `robotcode discover info`.

`info` is a static command — it just prints version/platform metadata
about the current Python and Robot Framework installation. The tests
pin the JSON schema (so consumers of `-f json discover info` can rely on
the field set) and check the TEXT output is a key:value list.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from robotcode.robot.utils import RF_VERSION

from .conftest import CliRunner

EXPECTED_JSON_KEYS = {
    "robotVersionString",
    "robotEnv",
    "robotcodeVersionString",
    "pythonVersionString",
    "executable",
    "machine",
    "processor",
    "platform",
    "system",
    "systemVersion",
}


def test_info_json_contains_expected_keys(robotcode_cli: CliRunner) -> None:
    """`Info` uses `CamelSnakeMixin` so JSON keys are camelCase, matching
    every other `discover` model. The schema is the public contract for
    `-f json discover info` consumers."""
    result = robotcode_cli(["--format", "json", "discover", "info"])
    data = json.loads(result.stdout)
    # `processor` may be empty on some platforms; `robotEnv` defaults to {}.
    must_have = EXPECTED_JSON_KEYS - {"processor"}
    assert must_have.issubset(set(data.keys()))


def test_info_robot_version_string_is_a_version(robotcode_cli: CliRunner) -> None:
    data = json.loads(robotcode_cli(["--format", "json", "discover", "info"]).stdout)
    assert re.match(r"^\d+\.\d+(\.\d+)?", data["robotVersionString"])


def test_info_python_version_string_is_a_version(robotcode_cli: CliRunner) -> None:
    data = json.loads(robotcode_cli(["--format", "json", "discover", "info"]).stdout)
    assert re.match(r"^\d+\.\d+\.\d+", data["pythonVersionString"])


def test_info_text_lists_key_value_pairs(robotcode_cli: CliRunner) -> None:
    """TEXT output is an italic-label bullet list with human-friendly labels."""
    result = robotcode_cli(["discover", "info"])
    assert "# Info" in result.stdout
    # Field labels appear in italic with their values inline.
    assert re.search(r"- _Robot Framework:_\s+\d+\.\d+", result.stdout)
    assert re.search(r"- _Python:_\s+\d+\.\d+", result.stdout)


def test_info_robot_env_echoed_when_set(robotcode_cli: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROBOT_OPTIONS", "--loglevel TRACE")
    data = json.loads(robotcode_cli(["--format", "json", "discover", "info"]).stdout)
    assert data["robotEnv"].get("ROBOT_OPTIONS") == "--loglevel TRACE"


def test_info_text_emits_italic_label_bullet_list(robotcode_cli: CliRunner) -> None:
    """The TEXT output is an italic-label bullet list (one bullet per
    info field). 2-column Field/Value tables would just carry a
    redundant "Field | Value" header, so we render them as bullets
    instead — same convention used by results' summary block."""
    out = robotcode_cli(["discover", "info"]).stdout
    assert out.startswith("# Info")
    # Every value line is an italic-label bullet; no markdown table appears.
    bullets = [line for line in out.splitlines() if line.startswith("- _")]
    assert bullets, "expected italic-label bullets in `discover info` output"
    assert not any(line.startswith("|") for line in out.splitlines())


# --- document formats --------------------------------------------------------------------------------------------

requires_markdown = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # a user-level robot.toml must not add extensions
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "project"
    root.mkdir()
    return root


def _document_formats(robotcode_cli: CliRunner, root: Path, *profiles: str) -> Any:
    args = ["--root", str(root), *(a for p in profiles for a in ("-p", p)), "--format", "json", "discover", "info"]
    return json.loads(robotcode_cli(args).stdout).get("documentFormats")


def _format(name: str, *extensions: str) -> Dict[str, Any]:
    return {"name": name, "extensions": list(extensions)}


@requires_markdown
def test_info_lists_the_formats_of_the_default_extensions(robotcode_cli: CliRunner, project: Path) -> None:
    (project / "robot.toml").write_text('output-dir = "results"\n', encoding="utf-8")

    assert _document_formats(robotcode_cli, project) == [
        _format("robot", "robot"),
        _format("json", "rbt"),
        _format("rest", "robot.rst"),
        _format("markdown", "robot.md"),
    ]


@pytest.mark.skipif(not ((6, 1) <= RF_VERSION < (7, 5)), reason="the default extensions of 6.1 to 7.4")
def test_info_lists_no_markdown_format_below_robot_framework_7_5(robotcode_cli: CliRunner, project: Path) -> None:
    (project / "robot.toml").write_text('output-dir = "results"\n', encoding="utf-8")

    assert _document_formats(robotcode_cli, project) == [
        _format("robot", "robot"),
        _format("json", "rbt"),
        _format("rest", "robot.rst"),
    ]


@requires_markdown
def test_info_lists_md_as_the_markdown_format(robotcode_cli: CliRunner, project: Path) -> None:
    (project / "robot.toml").write_text('extensions = "robot:md"\n', encoding="utf-8")

    assert _document_formats(robotcode_cli, project) == [_format("robot", "robot"), _format("markdown", "md")]


@pytest.mark.parametrize(
    ("extensions", "expected"),
    [("robot", [_format("robot", "robot")]), ("robot:txt", [_format("robot", "robot", "txt")])],
)
def test_info_lists_other_extensions_as_robot_frameworks_own_format(
    robotcode_cli: CliRunner, project: Path, extensions: str, expected: List[Dict[str, Any]]
) -> None:
    (project / "robot.toml").write_text(f'extensions = "{extensions}"\n', encoding="utf-8")

    assert _document_formats(robotcode_cli, project) == expected


@requires_markdown
def test_info_lists_the_extensions_of_a_selected_profile(robotcode_cli: CliRunner, project: Path) -> None:
    (project / "robot.toml").write_text('[profiles.docs]\nextensions = "robot:md"\n', encoding="utf-8")

    assert _format("markdown", "robot.md") in _document_formats(robotcode_cli, project)
    assert _document_formats(robotcode_cli, project, "docs") == [_format("robot", "robot"), _format("markdown", "md")]


@requires_markdown
def test_info_text_has_a_section_for_the_document_formats(robotcode_cli: CliRunner, project: Path) -> None:
    (project / "robot.toml").write_text('extensions = "robot:md:robot.md"\n', encoding="utf-8")

    out = robotcode_cli(["--root", str(project), "discover", "info"]).stdout

    assert "## Document Formats\n\n- _robot:_ `robot`\n- _markdown:_ `md`, `robot.md`" in out


def test_info_fails_for_an_unreadable_robot_toml(robotcode_cli: CliRunner, project: Path) -> None:
    (project / "robot.toml").write_text("extensions = \n", encoding="utf-8")

    result = robotcode_cli(["--root", str(project), "discover", "info"], expect_ok=False)

    assert result.returncode != 0
