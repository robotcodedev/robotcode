"""Tests for how `robot.toml` options reach the Robot Framework tools.

The console options are `robot` options; `rebot` of Robot Framework < 7.5
does not know them, so a top-level `console` must never be passed to it.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner
from robot.errors import INFO_PRINTED

from robotcode.cli import robotcode
from robotcode.robot.utils import RF_VERSION

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
