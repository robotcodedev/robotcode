from importlib import import_module
from pathlib import Path
from textwrap import dedent

import pytest
from robot.model import TagPatterns
from robot.version import get_version

pytestmark = pytest.mark.skipif(get_version() < "6.1", reason="Fast discovery tests require Robot Framework >= 6.1")

discover = import_module("robotcode.runner.cli.discover.discover")


def _write_robot(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def test_extract_force_tags_from_path_supports_continuation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discover, "_stdin_data", None)

    suite = tmp_path / "suite.robot"
    _write_robot(
        suite,
        """
        *** Settings ***
        Force Tags    parent    smoke
        ...    fast
        ...    smoke

        *** Test Cases ***
        Example
            No Operation
        """,
    )

    assert discover._extract_fast_file_data_from_path(suite).force_tags == ["parent", "smoke", "fast"]


def test_extract_force_tags_from_path_supports_test_tags_and_continuation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(discover, "_stdin_data", None)

    suite = tmp_path / "suite.robot"
    _write_robot(
        suite,
        """
        *** Settings ***
        Test Tags    smoke    api
        ...    fast

        *** Test Cases ***
        Example
            No Operation
        """,
    )

    assert discover._extract_fast_file_data_from_path(suite).force_tags == ["smoke", "api", "fast"]


def test_extract_default_tags_from_path_supports_continuation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discover, "_stdin_data", None)

    suite = tmp_path / "suite.robot"
    _write_robot(
        suite,
        """
        *** Settings ***
        Default Tags    smoke    api
        ...    fast

        *** Test Cases ***
        Example
            No Operation
        """,
    )

    assert discover._extract_fast_file_data_from_path(suite).default_tags == ["smoke", "api", "fast"]


def test_extract_default_tags_from_path_ignores_init_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discover, "_stdin_data", None)

    init_file = tmp_path / "__init__.robot"
    _write_robot(
        init_file,
        """
        *** Settings ***
        Default Tags    should_not_apply
        """,
    )

    assert discover._extract_fast_file_data_from_path(init_file).default_tags == []


def test_extract_suite_name_from_path_supports_name_setting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discover, "_stdin_data", None)

    suite = tmp_path / "suite.robot"
    _write_robot(
        suite,
        """
        *** Settings ***
        Name    Parent Suite Custom

        *** Test Cases ***
        Example
            No Operation
        """,
    )

    assert discover._extract_suite_name_from_path(suite) == "Parent Suite Custom"


def test_get_cached_inherited_force_tags_collects_parent_init_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(discover, "_stdin_data", None)

    level1 = tmp_path / "level1"
    level2 = level1 / "level2"
    level2.mkdir(parents=True)

    _write_robot(
        level1 / "__init__.robot",
        """
        *** Settings ***
        Force Tags    root
        """,
    )
    _write_robot(
        level2 / "__init__.robot",
        """
        *** Settings ***
        Force Tags    middle
        """,
    )

    suite = level2 / "suite.robot"
    _write_robot(
        suite,
        """
        *** Settings ***
        Force Tags    file

        *** Test Cases ***
        Example
            No Operation
        """,
    )

    allowed_suffixes = {".robot", ".resource"}
    force_tags_cache: dict[Path, list[str]] = {}
    inherited_cache: dict[Path, list[str]] = {}

    inherited = discover._get_cached_inherited_force_tags(
        suite,
        tmp_path,
        allowed_suffixes,
        force_tags_cache,
        inherited_cache,
    )

    assert set(inherited) == {"root", "middle", "file"}
    assert inherited[-1] == "file"


def test_get_cached_suite_name_for_directory_without_init_uses_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(discover, "_stdin_data", None)

    suite_dir = tmp_path / "238__SPSART2-2592_NM_Replacement_CGF"
    suite_dir.mkdir()

    allowed_suffixes = {".robot", ".resource"}
    suite_name_cache: dict[Path, str] = {}
    expected = discover.TestSuite.name_from_source(suite_dir)

    assert discover._get_cached_suite_name_for_path(suite_dir, allowed_suffixes, suite_name_cache) == expected


def test_extract_fast_items_from_path_collects_tags_with_continuation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(discover, "_stdin_data", None)

    suite = tmp_path / "suite.robot"
    _write_robot(
        suite,
        """
        *** Test Cases ***
        First Test
            [Tags]    smoke    fast
            ...    api
            No Operation

        Second Test
            [Tags]    db    db
            No Operation
        """,
    )

    items = discover._extract_fast_file_data_from_path(suite).items

    assert len(items) == 2

    first = items[0]
    assert first.item_type == "test"
    assert first.name == "First Test"
    assert first.lineno > 0
    assert first.tags == ["smoke", "fast", "api"]

    second = items[1]
    assert second.item_type == "test"
    assert second.name == "Second Test"
    assert second.lineno > 0
    assert second.tags == ["db"]


def test_fast_match_tags_applies_include_and_exclude_patterns() -> None:
    include = TagPatterns(["smoke"])
    exclude = TagPatterns(["flaky"])

    assert discover._fast_match_tags(["smoke", "api"], include, exclude)
    assert not discover._fast_match_tags(["api"], include, exclude)
    assert not discover._fast_match_tags(["smoke", "flaky"], include, exclude)


def test_apply_fast_tag_directives_supports_addition_and_deduplication() -> None:
    assert discover._apply_fast_tag_directives(
        ["root", "smoke"],
        ["api", "smoke", "fast"],
    ) == ["root", "smoke", "api", "fast"]


def test_compose_fast_effective_tags_applies_default_tags_only_without_tags_setting() -> None:
    assert discover._compose_fast_effective_tags(
        ["force"],
        ["default"],
        ["item"],
        False,
    ) == ["force", "default", "item"]
    assert discover._compose_fast_effective_tags(["force"], ["default"], ["item"], True) == ["force", "item"]


def test_compose_fast_effective_tags_supports_none_and_empty_override() -> None:
    assert discover._compose_fast_effective_tags(["force"], ["default"], [], True) == ["force"]
    assert discover._compose_fast_effective_tags(["force"], ["default"], ["NONE"], True) == ["force"]


def test_compose_fast_effective_tags_tags_minus_removes_inherited_test_tag() -> None:
    assert discover._compose_fast_effective_tags(["smoke", "api"], [], ["-smoke", "ui"], True) == ["api", "ui"]
