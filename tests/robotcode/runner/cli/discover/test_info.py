"""Acceptance tests for `robotcode discover info`.

`info` is a static command — it just prints version/platform metadata
about the current Python and Robot Framework installation. The tests
pin the JSON schema (so consumers of `-f json discover info` can rely on
the field set) and check the TEXT output is a key:value list.
"""

import json
import re

import pytest

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
