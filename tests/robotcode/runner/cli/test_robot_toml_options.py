"""Tests for how `robot.toml` options reach the Robot Framework tools.

The table of a tool (`[rebot]`, `[libdoc]`, `[testdoc]`) wins over the settings
outside of it, and each tool takes only some of those settings: `rebot` the ones
that Robot Framework itself passes from `robot` to `rebot` after a run, so not
the top-level console options; `libdoc` only `python-path`. The `[rebot]` table
has its own `console` and `quiet`, which `rebot` knows since Robot Framework 7.5.
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

    def run(robot_toml: str, *options: str, expect_dry_run: bool = True) -> Result:
        (tmp_path / "robot.toml").write_text(robot_toml, encoding="utf-8")
        result = CliRunner().invoke(robotcode, ["--no-color", "--no-pager", "--dry", *options, "rebot", "output.xml"])
        if expect_dry_run:
            # a dry run ends like `--help`: the options are printed instead of running the tool
            assert result.exit_code == INFO_PRINTED, result.output
            assert "Would execute rebot with the following options" in result.output
        return result

    return run


DryTool = Callable[..., Result]


@pytest.fixture
def dry_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DryTool:
    """Runs `robotcode --dry <tool> <args>` against the given `robot.toml` in an empty project."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    (tmp_path / "suite.robot").write_text("*** Test Cases ***\nTest\n    No Operation\n", encoding="utf-8")

    def run(robot_toml: str, tool: str, *args: str) -> Result:
        (tmp_path / "robot.toml").write_text(robot_toml, encoding="utf-8")
        result = CliRunner().invoke(robotcode, ["--no-color", "--no-pager", "--dry", tool, *args])
        assert result.exit_code == INFO_PRINTED, result.output
        assert f"Would execute {tool} with the following" in result.output
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


def test_top_level_console_is_not_passed_to_rebot(dry_rebot: DryRebot) -> None:
    result = dry_rebot('console = "dotted"\n\n[profiles.ci]\nreport-title = "From Profile"\n', "-p", "ci")

    # the configuration was used ...
    assert "reporttitle = 'From Profile'" in result.output
    # ... but the `robot` only option did not reach `rebot`
    assert "console = 'dotted'" not in result.output


def test_rebot_table_wins_over_the_settings_outside_of_it(dry_rebot: DryRebot) -> None:
    result = dry_rebot('output-dir = "results"\n\n[rebot]\noutput-dir = "merged"\n')

    assert "outputdir = 'merged'" in result.output


def test_rebot_takes_a_setting_from_outside_that_its_table_does_not_set(dry_rebot: DryRebot) -> None:
    result = dry_rebot('output-dir = "results"\n\n[rebot]\nmerge = true\n')

    assert "outputdir = 'results'" in result.output


def test_extend_setting_in_the_rebot_table_adds_to_the_setting_outside(dry_rebot: DryRebot) -> None:
    result = dry_rebot('tag-stat-include = ["smoke"]\n\n[rebot]\nextend-tag-stat-include = ["api"]\n')

    assert "tagstatinclude = ['smoke', 'api']" in result.output


def test_settings_that_robot_framework_does_not_pass_to_rebot_do_not_reach_it(dry_rebot: DryRebot) -> None:
    result = dry_rebot('includes = ["smoke"]\nname = "Shop"\noutput = "output.xml"\nlog-level = "DEBUG"\n')

    assert "include = ['smoke']" not in result.output
    assert "name = 'Shop'" not in result.output
    assert "output = 'output.xml'" not in result.output
    assert "loglevel = 'DEBUG'" not in result.output


def test_settings_that_robot_framework_passes_to_rebot_reach_it(dry_rebot: DryRebot) -> None:
    result = dry_rebot('report-title = "Nightly"\npython-path = ["libraries"]\n')

    assert "reporttitle = 'Nightly'" in result.output
    assert "pythonpath = ['libraries']" in result.output


def test_tasks_reach_rebot_as_robot_framework_passes_them(dry_rebot: DryRebot) -> None:
    result = dry_rebot('tasks = ["Process*"]\ntests = ["Login*"]\n')

    assert "task = ['Process*']" in result.output
    assert "test = ['Login*']" not in result.output


def test_run_empty_suite_reaches_rebot_as_process_empty_suite(dry_rebot: DryRebot) -> None:
    result = dry_rebot("run-empty-suite = true\n")

    assert "processemptysuite = True" in result.output


def test_process_empty_suite_of_the_rebot_table_wins_over_run_empty_suite(dry_rebot: DryRebot) -> None:
    result = dry_rebot("run-empty-suite = true\n\n[rebot]\nprocess-empty-suite = false\n")

    assert "processemptysuite = True" not in result.output


def test_settings_in_the_rebot_table_reach_rebot(dry_rebot: DryRebot) -> None:
    result = dry_rebot('[rebot]\nname = "Merged"\nincludes = ["smoke"]\n')

    assert "name = 'Merged'" in result.output
    assert "include = ['smoke']" in result.output


def test_extend_rebot_in_a_later_file_changes_the_rebot_table(dry_rebot: DryRebot, tmp_path: Path) -> None:
    (tmp_path / ".robot.toml").write_text('[extend-rebot]\nreport-title = "Mine"\n', encoding="utf-8")

    result = dry_rebot("[rebot]\nmerge = true\n")

    assert "merge = True" in result.output
    assert "reporttitle = 'Mine'" in result.output


def test_extend_rebot_in_a_profile_changes_the_rebot_table(dry_rebot: DryRebot) -> None:
    result = dry_rebot('[rebot]\nmerge = true\n\n[profiles.ci.extend-rebot]\nlog-title = "CI"\n', "-p", "ci")

    assert "merge = True" in result.output
    assert "logtitle = 'CI'" in result.output


def test_extend_setting_in_extend_rebot_of_a_later_file_adds_to_the_setting_outside(
    dry_rebot: DryRebot, tmp_path: Path
) -> None:
    (tmp_path / ".robot.toml").write_text('[extend-rebot]\nextend-tag-stat-include = ["api"]\n', encoding="utf-8")

    result = dry_rebot('tag-stat-include = ["smoke"]\n\n[rebot]\nmerge = true\n')

    assert "merge = True" in result.output
    assert "tagstatinclude = ['smoke', 'api']" in result.output


def test_extend_settings_of_the_rebot_table_and_extend_rebot_add_up(dry_rebot: DryRebot, tmp_path: Path) -> None:
    (tmp_path / ".robot.toml").write_text('[extend-rebot]\nextend-tag-stat-include = ["b"]\n', encoding="utf-8")

    result = dry_rebot('tag-stat-include = ["smoke"]\n\n[rebot]\nextend-tag-stat-include = ["a"]\n')

    assert "tagstatinclude = ['smoke', 'a', 'b']" in result.output


def test_extend_setting_in_extend_rebot_of_a_profile_adds_to_the_setting_outside(dry_rebot: DryRebot) -> None:
    result = dry_rebot(
        'tag-stat-include = ["smoke"]\n\n[rebot]\nmerge = true\n\n'
        '[profiles.ci.extend-rebot]\nextend-tag-stat-include = ["ci"]\n',
        "-p",
        "ci",
    )

    assert "merge = True" in result.output
    assert "tagstatinclude = ['smoke', 'ci']" in result.output


def test_extend_setting_in_extend_rebot_of_extend_profiles_adds_to_the_setting_outside(
    dry_rebot: DryRebot, tmp_path: Path
) -> None:
    (tmp_path / ".robot.toml").write_text(
        '[extend-profiles.ci.extend-rebot]\nextend-tag-stat-include = ["mine"]\n', encoding="utf-8"
    )

    result = dry_rebot('tag-stat-include = ["smoke"]\n\n[profiles.ci.rebot]\nmerge = true\n', "-p", "ci")

    assert "merge = True" in result.output
    assert "tagstatinclude = ['smoke', 'mine']" in result.output


@pytest.mark.skipif(RF_VERSION < (6, 0), reason="libdoc knows --theme since Robot Framework 6.0")
def test_extend_libdoc_in_a_later_file_changes_the_libdoc_table(dry_tool: DryTool, tmp_path: Path) -> None:
    (tmp_path / ".robot.toml").write_text('[extend-libdoc]\ntheme = "DARK"\n', encoding="utf-8")

    result = dry_tool('[libdoc]\nformat = "HTML"\n', "libdoc", "Collections", "out.html")

    assert "format = 'HTML'" in result.output
    assert "theme = 'DARK'" in result.output


def test_extend_testdoc_in_a_later_file_changes_the_testdoc_table(dry_tool: DryTool, tmp_path: Path) -> None:
    (tmp_path / ".robot.toml").write_text('[extend-testdoc]\nname = "Shop Tests"\n', encoding="utf-8")

    result = dry_tool('[testdoc]\ntitle = "Shop"\n', "testdoc", "suite.robot", "out.html")

    assert "title = 'Shop'" in result.output
    assert "name = 'Shop Tests'" in result.output


def test_libdoc_takes_only_the_python_path_from_outside_its_table(dry_tool: DryTool) -> None:
    result = dry_tool(
        'name = "Shop Tests"\nquiet = true\npython-path = ["libraries"]\n', "libdoc", "Collections", "out.html"
    )

    assert "name = 'Shop Tests'" not in result.output
    assert "quiet = True" not in result.output
    assert "pythonpath = ['libraries']" in result.output


def test_libdoc_table_wins_over_the_python_path_outside_of_it(dry_tool: DryTool) -> None:
    result = dry_tool(
        'python-path = ["libraries"]\n\n[libdoc]\npython-path = ["doc-libraries"]\n',
        "libdoc",
        "Collections",
        "out.html",
    )

    assert "pythonpath = ['doc-libraries']" in result.output


def test_testdoc_table_wins_over_the_name_outside_of_it(dry_tool: DryTool) -> None:
    result = dry_tool('name = "Shop"\n\n[testdoc]\nname = "Shop Tests"\n', "testdoc", "suite.robot", "out.html")

    assert "name = 'Shop Tests'" in result.output


def test_testdoc_takes_the_settings_it_shares_with_robot(dry_tool: DryTool) -> None:
    result = dry_tool('name = "Shop"\nincludes = ["smoke"]\n', "testdoc", "suite.robot", "out.html")

    assert "name = 'Shop'" in result.output
    assert "include = ['smoke']" in result.output


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
