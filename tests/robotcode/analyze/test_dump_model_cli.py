"""Acceptance tests for the hidden `robotcode analyze dump-model` command.

In-process invocation of the real `robotcode` Click group via CliRunner —
builds a real namespace (imports, builtin variables) for a small project in
`tmp_path` and checks the JSON dump surface per the
`semantic-model-inspection` spec.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from robotcode.cli import robotcode

_SUITE = """\
*** Variables ***
${GREETING}    hello

*** Test Cases ***
Test One
    ${result}=    Set Variable    ${GREETING}
    IF    $result == 'hello'
        Log    ${result}
    END
"""


@pytest.fixture
def suite_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    suite = tmp_path / "suite.robot"
    suite.write_text(_SUITE, encoding="utf-8")
    return suite


def test_dump_to_stdout(suite_file: Path) -> None:
    result = CliRunner().invoke(robotcode, ["analyze", "dump-model", str(suite_file)])
    assert result.exit_code == 0, result.output
    dump = json.loads(result.output)
    assert set(dump.keys()) == {"source", "tree", "statements", "file_scope", "local_scopes"}
    assert dump["tree"]["kind"] == "FILE"
    assert dump["statements"]
    # The experimental flag is not enabled in this project — the command
    # forces the semantic-model build anyway.
    assert any(v["name"] == "${GREETING}" for v in dump["file_scope"]["own"])
    assert dump["file_scope"]["builtin"]


def test_dump_to_file(suite_file: Path, tmp_path: Path) -> None:
    out = tmp_path / "model.json"
    result = CliRunner().invoke(robotcode, ["analyze", "dump-model", str(suite_file), "-o", str(out)])
    assert result.exit_code == 0, result.output
    dump = json.loads(out.read_text(encoding="utf-8"))
    assert dump["statements"]


def test_nonexistent_file_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(robotcode, ["analyze", "dump-model", "does-not-exist.robot"])
    assert result.exit_code != 0
