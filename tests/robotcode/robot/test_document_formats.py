"""Tests for the document formats Robot Framework parses with a profile and the Markdown files RobotCode serves."""

import inspect
from pathlib import Path
from typing import List, Optional

import pytest
from robot.running import builder

from robotcode.robot.config.loader import load_robot_config_from_robot_toml_str
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.document_formats import (
    MARKDOWN_SUPPORTED,
    DocumentFormat,
    document_formats,
    markdown_extensions,
    parse_include_condition,
)
from robotcode.robot.utils import RF_VERSION

requires_markdown = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")


def _markdown(toml: str, *profiles: str) -> List[str]:
    profile = load_robot_config_from_robot_toml_str(toml).combine_profiles(*profiles).evaluated()
    return markdown_extensions(profile)


def test_the_default_extensions_are_robot_frameworks() -> None:
    default = inspect.signature(builder.TestSuiteBuilder.__init__).parameters["included_extensions"].default

    assert [e for f in document_formats(RobotBaseProfile()) for e in f.extensions] == [e.lstrip(".") for e in default]


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="Robot Framework parses Markdown since 7.5")
def test_the_formats_of_the_default_extensions() -> None:
    assert document_formats(RobotBaseProfile()) == [
        DocumentFormat("robot", ["robot"]),
        DocumentFormat("json", ["rbt"]),
        DocumentFormat("rest", ["robot.rst"]),
        DocumentFormat("markdown", ["robot.md"]),
    ]


@pytest.mark.skipif(not ((6, 1) <= RF_VERSION < (7, 5)), reason="the default extensions of 6.1 to 7.4")
def test_no_markdown_format_below_robot_framework_7_5() -> None:
    assert document_formats(RobotBaseProfile()) == [
        DocumentFormat("robot", ["robot"]),
        DocumentFormat("json", ["rbt"]),
        DocumentFormat("rest", ["robot.rst"]),
    ]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("robot", [DocumentFormat("robot", ["robot"])]),
        ("robot:txt", [DocumentFormat("robot", ["robot", "txt"])]),
        ("robot:rst", [DocumentFormat("robot", ["robot"]), DocumentFormat("rest", ["rst"])]),
    ],
)
def test_other_extensions_are_robot_frameworks_own_format(value: str, expected: List[DocumentFormat]) -> None:
    assert document_formats(RobotBaseProfile(extensions=value)) == expected


@requires_markdown
def test_md_in_extensions_is_the_markdown_format() -> None:
    assert document_formats(RobotBaseProfile(extensions="robot:md")) == [
        DocumentFormat("robot", ["robot"]),
        DocumentFormat("markdown", ["md"]),
    ]


@requires_markdown
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("robot:robot.md", ["robot.md"]),
        ("robot:MD", ["md"]),
        (".md", ["md"]),
        ("robot:md:markdown", ["md", "markdown"]),
        ("robot:md:.MD", ["md"]),
    ],
)
def test_markdown_extensions_of_the_option_are_served(value: str, expected: List[str]) -> None:
    assert _markdown(f'extensions = "{value}"') == expected


@requires_markdown
def test_an_expression_value_is_evaluated() -> None:
    assert _markdown("extensions = { expr = \"'robot:' + 'md'\" }") == ["md"]


@requires_markdown
def test_the_extensions_of_a_selected_profile_count() -> None:
    toml = """
        [profiles.docs]
        extensions = "robot:md"
        """
    assert _markdown(toml) == ["robot.md"]
    assert _markdown(toml, "docs") == ["md"]


@requires_markdown
def test_robot_md_is_served_by_robot_frameworks_default_extensions() -> None:
    assert markdown_extensions(RobotBaseProfile()) == ["robot.md"]


@pytest.mark.parametrize("value", ["robot", "robot:txt"])
def test_no_markdown_without_a_markdown_extension(value: str) -> None:
    assert markdown_extensions(RobotBaseProfile(extensions=value)) == []


@requires_markdown
@pytest.mark.parametrize(
    ("extensions", "patterns", "expected"),
    [
        ("robot", ["docs/*.md"], ["md"]),
        (None, ["*.robot.md"], ["robot.md", "md"]),
        (None, ["docs"], ["robot.md"]),
        ("robot", ["tests/*.robot"], []),
    ],
)
def test_the_extension_of_a_parse_include_pattern_counts(
    extensions: Optional[str], patterns: List[str], expected: List[str]
) -> None:
    assert markdown_extensions(RobotBaseProfile(extensions=extensions, parse_include=list(patterns))) == expected


@pytest.mark.parametrize("extensions", [None, "robot:md"])
def test_no_markdown_below_robot_framework_7_5_1(monkeypatch: pytest.MonkeyPatch, extensions: Optional[str]) -> None:
    monkeypatch.setattr("robotcode.robot.document_formats.MARKDOWN_SUPPORTED", False)

    assert markdown_extensions(RobotBaseProfile(extensions=extensions)) == []


def test_no_condition_without_parse_include_patterns(tmp_path: Path) -> None:
    assert parse_include_condition(RobotBaseProfile(), tmp_path) is None


@requires_markdown
@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("*.robot.md", "tests/sub/shop.robot.md", True),
        ("*.robot.md", "README.md", False),
        ("docs/*.md", "docs/guide.md", True),
        ("docs/*.md", "other/docs/guide.md", False),
        ("docs", "docs/sub/guide.md", True),
        ("docs", "guide.md", False),
        ("docs/*.md", "other/__init__.md", True),
        ("docs/*.md", "other/__init__.robot.md", False),
    ],
)
def test_the_parse_include_patterns_match_like_robot_framework_from_the_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pattern: str, path: str, expected: bool
) -> None:
    root = tmp_path / "project"
    (root / "docs").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    condition = parse_include_condition(RobotBaseProfile(parse_include=[pattern]), root)

    assert condition is not None
    assert condition(root / path) is expected
