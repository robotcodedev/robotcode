"""`robotcode config info` finds a setting by its exact name, also one that holds pattern characters."""

import pytest
from click.testing import CliRunner

from robotcode.cli import robotcode as robotcode_cli


@pytest.mark.parametrize("name", ["[profile].precedence", "*.precedence"])
def test_desc_finds_a_setting_by_name_or_pattern(name: str) -> None:
    result = CliRunner().invoke(robotcode_cli, ["config", "info", "desc", name], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "[profile].precedence" in result.stdout
    assert "precedence" in result.stdout.split("[profile].precedence", 1)[1]


def test_list_finds_a_setting_by_its_exact_name() -> None:
    args = ["config", "info", "list", "[profile].precedence"]

    result = CliRunner().invoke(robotcode_cli, args, catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "[profile].precedence" in result.stdout
