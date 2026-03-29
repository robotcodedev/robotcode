import os
import os.path
import sys
from os import PathLike
from typing import List, Optional, Union

_PathLike = Union[str, "PathLike[str]"]

# Cache of sys.path entries that are valid directories.
# Populated lazily on first use; call invalidate_sys_path_cache()
# if sys.path changes during the process lifetime.
_valid_sys_path: Optional[List[str]] = None


def _get_valid_sys_path() -> List[str]:
    global _valid_sys_path
    if _valid_sys_path is None:
        _valid_sys_path = [p for p in sys.path if p and os.path.isdir(p)]
    return _valid_sys_path


def invalidate_sys_path_cache() -> None:
    global _valid_sys_path
    _valid_sys_path = None


def find_file_ex(
    path: _PathLike,
    basedir: _PathLike = ".",
    file_type: Optional[str] = None,
) -> str:
    from robot.errors import DataError

    ret = _find_absolute_path(path) if os.path.isabs(path) else _find_relative_path(path, basedir)
    if ret:
        return ret

    default = file_type or "File"

    file_type = (
        {
            "Library": "Test library",
            "Variables": "Variable file",
            "Resource": "Resource file",
        }.get(file_type, default)
        if file_type
        else default
    )

    raise DataError("%s '%s' does not exist." % (file_type, path))


def find_file(
    path: _PathLike,
    basedir: _PathLike = ".",
    file_type: Optional[str] = None,
) -> str:
    return find_file_ex(path, basedir, file_type)


def _find_absolute_path(path: _PathLike) -> Optional[str]:
    if _is_valid_file(path):
        return os.fspath(path)
    return None


def _find_relative_path(path: _PathLike, basedir: _PathLike) -> Optional[str]:
    if basedir and os.path.isdir(basedir):
        candidate = os.path.abspath(os.path.join(basedir, path))
        if _is_valid_file(candidate):
            return candidate

    for base in _get_valid_sys_path():
        candidate = os.path.abspath(os.path.join(base, path))
        if _is_valid_file(candidate):
            return candidate

    return None


def _is_valid_file(path: _PathLike) -> bool:
    return os.path.isfile(path) or (os.path.isdir(path) and os.path.isfile(os.path.join(path, "__init__.py")))
