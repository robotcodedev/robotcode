import dataclasses
import os
import pickle
from pathlib import Path

import pytest

from robotcode.core.utils.path import (
    RACY_MTIME_EPSILON_NS,
    DiskInfo,
    disk_info_from_stat,
    probe_disk_info,
)


def _backdate(path: Path, ns: int) -> None:
    t = os.stat(path).st_mtime_ns - ns
    os.utime(path, ns=(t, t))


def test_equality_ignores_trusted() -> None:
    assert DiskInfo(1, 2, trusted=True) == DiskInfo(1, 2, trusted=False)


def test_equality_compares_mtime_and_size() -> None:
    assert DiskInfo(1, 2) != DiskInfo(2, 2)
    assert DiskInfo(1, 2) != DiskInfo(1, 3)


def test_is_frozen() -> None:
    info = DiskInfo(1, 2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.mtime_ns = 3  # type: ignore[misc]


def test_pickle_roundtrip_preserves_all_fields() -> None:
    info = DiskInfo(1, 2, trusted=False)
    loaded = pickle.loads(pickle.dumps(info))
    assert loaded == info
    assert loaded.trusted is False


def test_from_stat_backdated_file_is_trusted(tmp_path: Path) -> None:
    file = tmp_path / "a.txt"
    file.write_text("hello")
    _backdate(file, RACY_MTIME_EPSILON_NS * 5)

    info = disk_info_from_stat(os.stat(file))

    assert info.trusted is True
    assert info.size == 5


def test_from_stat_fresh_file_is_untrusted(tmp_path: Path) -> None:
    file = tmp_path / "a.txt"
    file.write_text("hello")

    st = os.stat(file)
    info = disk_info_from_stat(st, now_ns=st.st_mtime_ns + 1)

    assert info.trusted is False


def test_from_stat_future_mtime_is_untrusted(tmp_path: Path) -> None:
    file = tmp_path / "a.txt"
    file.write_text("hello")

    st = os.stat(file)
    info = disk_info_from_stat(st, now_ns=st.st_mtime_ns - RACY_MTIME_EPSILON_NS)

    assert info.trusted is False


def test_probe_returns_current_state(tmp_path: Path) -> None:
    file = tmp_path / "a.txt"
    file.write_text("hello")
    _backdate(file, RACY_MTIME_EPSILON_NS * 5)

    st = os.stat(file)
    info = probe_disk_info(file)

    assert info is not None
    assert info.mtime_ns == st.st_mtime_ns
    assert info.size == st.st_size
    assert info.trusted is True


def test_probe_missing_file_returns_none(tmp_path: Path) -> None:
    assert probe_disk_info(tmp_path / "missing.txt") is None
