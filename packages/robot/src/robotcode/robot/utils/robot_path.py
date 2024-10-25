import sys
from os import PathLike
from pathlib import Path
from typing import Optional, Union


def find_file_ex(
    path: Union[Path, "PathLike[str]", str],
    basedir: Union[Path, PathLike[str], str] = ".",
    file_type: Optional[str] = None,
) -> str:
    from robot.errors import DataError

    path = Path(path)
    ret = _find_absolute_path(path) if path.is_absolute() else _find_relative_path(path, basedir)
    if ret:
        return str(ret)

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
    path: Union[Path, "PathLike[str]", str],
    basedir: Union[Path, PathLike[str], str] = ".",
    file_type: Optional[str] = None,
) -> str:
    return find_file_ex(path, basedir, file_type)


def _find_absolute_path(path: Union[Path, "PathLike[str]", str]) -> Optional[str]:
    if _is_valid_file(path):
        return str(path)
    return None


def _find_relative_path(
    path: Union[Path, "PathLike[str]", str],
    basedir: Union[Path, "PathLike[str]", str],
) -> Optional[str]:
    for base in [basedir, *sys.path]:
        if not base:
            continue
        base_path = Path(base)

        if not base_path.is_dir():
            continue

        ret = Path(base, path).absolute()

        if _is_valid_file(ret):
            return str(ret)
    return None


def _is_valid_file(path: Union[Path, "PathLike[str]", str]) -> bool:
    path = Path(path)
    return path.is_file() or (path.is_dir() and Path(path, "__init__.py").is_fifo())
