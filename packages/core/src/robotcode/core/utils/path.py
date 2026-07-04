import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Optional, Tuple, Union


def path_is_relative_to(
    path: Union[Path, str, "os.PathLike[Any]"],
    other_path: Union[Path, str, "os.PathLike[Any]"],
) -> bool:
    try:
        Path(path).relative_to(other_path)
        return True
    except ValueError:
        return False


def try_get_relative_path(
    path: Union[str, "os.PathLike[str]"], other_path: Union[str, "os.PathLike[str]", None]
) -> Path:
    if other_path is None:
        return Path(path)
    try:
        return Path(path).relative_to(other_path)
    except ValueError:
        return Path(path)


_RE_DRIVE_LETTER_PATH = re.compile(r"^[a-zA-Z]:")


def normalized_path(path: "Union[str, os.PathLike[str]]") -> Path:
    p = os.path.normpath(os.path.abspath(path))

    if sys.platform == "win32" and _RE_DRIVE_LETTER_PATH.match(str(p)):
        return Path(p[0].upper() + p[1:])

    return Path(p)


def normalized_path_full(path: Union[str, "os.PathLike[str]"]) -> Path:
    p = normalized_path(path)

    orig_parents = list(reversed(p.parents))
    orig_parents.append(p)

    parents = []
    for index, parent in enumerate(orig_parents):
        if parent.exists():
            ps = (
                next((f.name for f in parent.parent.iterdir() if f.samefile(parent)), None)
                if parent.parent is not None and parent.parent != parent
                else parent.name or parent.anchor
            )

            parents.append(ps if ps is not None else parent.name)
        else:
            return Path(*parents, *[f.name for f in orig_parents[index:]])

    return Path(*parents)


FileId = Tuple[int, int]


def file_id(path: Union[str, "os.PathLike[str]", Path]) -> Optional[FileId]:
    """Return the (st_dev, st_ino) tuple for *path*, or ``None`` on error."""
    try:
        st = os.stat(path)
        return (st.st_dev, st.st_ino)
    except OSError:
        return None


def same_file(path1: Union[str, "os.PathLike[str]", Path], path2: Union[str, "os.PathLike[str]", Path]) -> bool:
    try:
        return os.path.samefile(path1, path2)
    except OSError:
        return False


def same_file_id(
    id1: Optional[FileId],
    id2: Optional[FileId],
) -> bool:
    """Compare two :func:`file_id` values. ``None`` never matches anything."""
    if id1 is None or id2 is None:
        return False
    return id1 == id2


RACY_MTIME_EPSILON_NS: Final = 2_000_000_000
"""Snapshot age below which a file state is not trusted for persistent caching.

Analogous to git's "racily clean" handling: if a file's mtime is within this
epsilon of the current time when its content is read, a later write could land
in the same filesystem timestamp tick and leave mtime and size unchanged, so
the snapshot must not be persisted. 2 s covers the coarsest common filesystem
timestamp granularity (FAT).

Known limitation: the age is computed against the local clock, so on a network
mount whose server clock trails the client by more than the epsilon a
just-written file already counts as trusted — the stat-only design cannot
detect that; a content hash would be required to close it.
"""


@dataclass(frozen=True)
class DiskInfo:
    """Stat snapshot taken at the moment file content was read from disk.

    Equality compares only ``mtime_ns`` and ``size`` — ``trusted`` describes the
    capture moment (see ``RACY_MTIME_EPSILON_NS``), not the file state, and must
    never influence comparisons of stored metadata against fresh probes.

    Deliberately carries no ``st_ino``: file IDs are 0 or unstable on
    FAT/exFAT/ReFS and change across SMB/FUSE remounts, which would invalidate
    caches spuriously; the racy-mtime guard already covers the same-tick
    rewrite case an inode check would catch.
    """

    mtime_ns: int
    size: int
    trusted: bool = field(default=True, compare=False)


def disk_info_from_stat(st: os.stat_result, now_ns: Optional[int] = None) -> DiskInfo:
    if now_ns is None:
        now_ns = time.time_ns()
    return DiskInfo(
        mtime_ns=st.st_mtime_ns,
        size=st.st_size,
        # a negative age (mtime in the future, e.g. clock skew) is also untrusted
        trusted=now_ns - st.st_mtime_ns >= RACY_MTIME_EPSILON_NS,
    )


def probe_disk_info(path: Union[str, "os.PathLike[str]"]) -> Optional[DiskInfo]:
    """Return the current :class:`DiskInfo` for *path*, or ``None`` on error."""
    try:
        return disk_info_from_stat(os.stat(path))
    except OSError:
        return None
