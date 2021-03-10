from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import Any, Union


def path_is_relative_to(path: Union[Path, str, PathLike[Any]], other_path: Union[Path, str, PathLike[Any]]) -> bool:
    try:
        Path(path).relative_to(other_path)
        return True
    except ValueError:
        return False
