"""Tests for how `robot.toml` options reach the Robot Framework tools.

The top-level console options are `robot` options and never reach `rebot`;
the `[rebot]` section has its own `console` and `quiet`, which `rebot` knows
since Robot Framework 7.5.
"""

from pathlib import Path
from typing import Callable

import pytest
from click.testing import CliRunner, Result
from robot.errors import DATA_ERROR, INFO_PRINTED

import robotcode.robot.config.utils as config_utils
from robotcode.cli import robotcode
from robotcode.robot.utils import RF_VERSION

from .rf_markers import needs_rf_75

OUTPUT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 7.0" generated="2024-01-01T00:00:00.000000" rpa="false" schemaversion="5">
<suite id="s1" name="Suite" source="/suite.robot">
<test id="s1-t1" name="Test" line="2">
<status status="PASS" start="2024-01-01T00:00:00.000000" elapsed="0.001"/>
</test>
<status status="PASS" start="2024-01-01T00:00:00.000000" elapsed="0.002"/>
</suite>
<statistics>
<total>
<stat pass="1" fail="0" skip="0">All Tests</stat>
</total>
<tag>
</tag>
<suite>
<stat name="Suite" id="s1" pass="1" fail="0" skip="0">Suite</stat>
</suite>
</statistics>
<errors>
</errors>
</robot>
"""


DryRebot = Callable[..., Result]


@pytest.fixture
def dry_rebot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DryRebot:
    """Runs `robotcode --dry rebot output.xml` against the given `robot.toml` in an empty project."""
    monkeypatch.chdir(tmp_path)
    # keep a developer's user-level robot.toml and the option environment variables out of the test
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    monkeypatch.delenv("ROBOT_OPTIONS", raising=False)
    monkeypatch.delenv("REBOT_OPTIONS", raising=False)
    (tmp_path / "output.xml").write_text(OUTPUT_XML, encoding="utf-8")

    def run(robot_toml: str, *, expect_dry_run: bool = True) -> Result:
        (tmp_path / "robot.toml").write_text(robot_toml, encoding="utf-8")
        result = CliRunner().invoke(robotcode, ["--no-color", "--no-pager", "--dry", "rebot", "output.xml"])
        if expect_dry_run:
            # a dry run ends like `--help`: the options are printed instead of running the tool
            assert result.exit_code == INFO_PRINTED, result.output
            assert "Would execute rebot with the following options" in result.output
        return result

    return run


_REBOT_CONSOLE_CONFIGS = [
    pytest.param('[rebot]\nconsole = "quiet"\n', "console = 'quiet'", id="console"),
    pytest.param("[rebot]\nquiet = true\n", "quiet = True", id="quiet"),
    pytest.param(
        '[rebot]\nconsole = "path/to/Console.py:arg"\n', "console = 'path/to/Console.py:arg'", id="custom-console"
    ),
]


@needs_rf_75
@pytest.mark.parametrize(("robot_toml", "expected_line"), _REBOT_CONSOLE_CONFIGS)
def test_rebot_console_options_are_passed_to_rebot(robot_toml: str, expected_line: str, dry_rebot: DryRebot) -> None:
    assert expected_line in dry_rebot(robot_toml).output


@pytest.mark.skipif(
    not (7, 1) <= RF_VERSION < (7, 5),
    reason="rebot knows --console and --quiet since Robot Framework 7.5; before 7.1 it reads "
    "`--console` as a prefix of `--consolecolors` and rejects the value instead of the option",
)
@pytest.mark.parametrize(("robot_toml", "expected_line"), _REBOT_CONSOLE_CONFIGS)
def test_rebot_rejects_the_console_options_on_older_robot(
    robot_toml: str, expected_line: str, dry_rebot: DryRebot
) -> None:
    """The options are passed on every version; `rebot` itself rejects the ones it does not know
    (`option --console not a unique prefix`) before the dry run gets to print anything."""
    result = dry_rebot(robot_toml, expect_dry_run=False)

    assert result.exit_code == DATA_ERROR, result.output
    assert "Would execute rebot" not in result.output


def test_top_level_console_options_do_not_apply_to_rebot(dry_rebot: DryRebot) -> None:
    result = dry_rebot('console = "dotted"\nquiet = true\n')

    assert "console = 'dotted'" not in result.output
    assert "quiet = True" not in result.output


def test_top_level_console_is_not_passed_to_rebot(tmp_path: Path) -> None:
    config_file = tmp_path / "robot.toml"
    config_file.write_text(
        'console = "dotted"\n\n[profiles.ci]\nname = "From Profile"\n',
        encoding="utf-8",
    )
    output_file = tmp_path / "output.xml"
    output_file.write_text(OUTPUT_XML, encoding="utf-8")

    result = CliRunner().invoke(
        robotcode,
        ["--no-color", "--no-pager", "--dry", "-c", str(config_file), "-p", "ci", "rebot", str(output_file)],
    )

    # a dry run ends like `--help`: the options are printed instead of running the tool
    assert result.exit_code == INFO_PRINTED, result.output
    # the configuration was used ...
    assert "name = 'From Profile'" in result.output
    # ... but the `robot` only option did not reach `rebot`
    assert "console = 'dotted'" not in result.output


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="Libdoc writes Markdown since RF 7.5")
def test_libdoc_writes_markdown_when_configured(tmp_path: Path) -> None:
    config_file = tmp_path / "robot.toml"
    config_file.write_text('[libdoc]\nformat = "MARKDOWN"\n', encoding="utf-8")
    output_file = tmp_path / "Collections.md"

    result = CliRunner().invoke(
        robotcode,
        ["--no-color", "--no-pager", "-c", str(config_file), "libdoc", "Collections", str(output_file)],
    )

    assert result.exit_code == 0, result.output
    assert output_file.is_file()
    assert "Append To List" in output_file.read_text(encoding="utf-8")
