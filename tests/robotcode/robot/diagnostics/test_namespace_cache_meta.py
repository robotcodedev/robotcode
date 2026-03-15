import sys
from pathlib import Path

import pytest

from robotcode.robot.diagnostics.data_cache import CacheSection
from robotcode.robot.diagnostics.imports_manager import NamespaceCacheMeta, RobotFileMeta


def test_cache_section_has_namespace() -> None:
    assert CacheSection.NAMESPACE.value == "namespace"


def test_cache_section_has_all_expected_values() -> None:
    values = {s.value for s in CacheSection}
    assert "libdoc" in values
    assert "variables" in values
    assert "resource" in values
    assert "namespace" in values


def test_namespace_cache_meta_has_python_executable_field() -> None:
    meta = NamespaceCacheMeta(
        meta_version="1.0.0",
        source="/some/path/test.robot",
        mtime_ns=123456789,
        python_executable=sys.executable,
    )
    assert meta.python_executable == sys.executable


def test_namespace_cache_meta_filepath_base(tmp_path: Path) -> None:
    source = tmp_path / "mytest.robot"
    meta = NamespaceCacheMeta(
        meta_version="1.0.0",
        source=str(source),
        mtime_ns=123456789,
        python_executable=sys.executable,
    )
    filepath_base = meta.filepath_base
    assert filepath_base.endswith("_mytest.robot")
    assert len(filepath_base) > 0


def test_namespace_cache_meta_equality() -> None:
    meta1 = NamespaceCacheMeta(
        meta_version="1.0.0",
        source="/some/path/test.robot",
        mtime_ns=123456789,
        python_executable=sys.executable,
    )
    meta2 = NamespaceCacheMeta(
        meta_version="1.0.0",
        source="/some/path/test.robot",
        mtime_ns=123456789,
        python_executable=sys.executable,
    )
    assert meta1 == meta2


def test_namespace_cache_meta_differs_by_python_executable() -> None:
    meta1 = NamespaceCacheMeta(
        meta_version="1.0.0",
        source="/some/path/test.robot",
        mtime_ns=123456789,
        python_executable="/usr/bin/python3",
    )
    meta2 = NamespaceCacheMeta(
        meta_version="1.0.0",
        source="/some/path/test.robot",
        mtime_ns=123456789,
        python_executable="/home/user/.venv/bin/python3",
    )
    assert meta1 != meta2


def test_namespace_cache_meta_differs_by_mtime() -> None:
    meta1 = NamespaceCacheMeta(
        meta_version="1.0.0",
        source="/some/path/test.robot",
        mtime_ns=111111111,
        python_executable=sys.executable,
    )
    meta2 = NamespaceCacheMeta(
        meta_version="1.0.0",
        source="/some/path/test.robot",
        mtime_ns=222222222,
        python_executable=sys.executable,
    )
    assert meta1 != meta2


def test_robot_file_meta_unchanged() -> None:
    meta = RobotFileMeta(
        meta_version="1.0.0",
        source="/some/path/test.robot",
        mtime_ns=123456789,
    )
    assert not hasattr(meta, "python_executable")


def test_get_namespace_meta_returns_meta_for_existing_file(tmp_path: Path) -> None:
    from robotcode.robot.diagnostics.imports_manager import ImportsManager

    robot_file = tmp_path / "test.robot"
    robot_file.write_text("*** Test Cases ***\n", encoding="utf-8")

    meta = ImportsManager.get_namespace_meta(str(robot_file))
    assert meta is not None
    assert meta.source == str(robot_file)
    assert meta.python_executable == sys.executable
    assert meta.mtime_ns > 0


def test_get_namespace_meta_returns_none_for_missing_file(tmp_path: Path) -> None:
    from robotcode.robot.diagnostics.imports_manager import ImportsManager

    missing_file = tmp_path / "nonexistent.robot"
    meta = ImportsManager.get_namespace_meta(str(missing_file))
    assert meta is None
