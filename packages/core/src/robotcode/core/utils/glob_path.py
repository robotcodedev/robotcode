# mypy: warn_unused_ignores=false

from __future__ import annotations

import functools
import os
import re
from pathlib import Path, PurePath
from typing import Any, Iterable, Iterator, Optional, Sequence, Union, cast


def _glob_pattern_to_re(pattern: str) -> str:
    result = "(?ms)^"

    in_group = False

    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c in "\\/$^+.()=!|":
            result += "\\" + c
        elif c == "?":
            result += "."
        elif c in "[]":
            result += c
        elif c == "{":
            in_group = True
            result += "("
        elif c == "}":
            in_group = False
            result += ")"
        elif c == ",":
            if in_group:
                result += "|"
            else:
                result += "\\" + c
        elif c == "*":
            prev_char = pattern[i - 1] if i > 0 else None
            star_count = 1

            while (i + 1) < len(pattern) and pattern[i + 1] == "*":
                star_count += 1
                i += 1

            next_char = pattern[i + 1] if (i + 1) < len(pattern) else None

            is_globstar = (
                star_count > 1 and (prev_char is None or prev_char == "/") and (next_char is None or next_char == "/")
            )

            if is_globstar:
                result += "((?:[^/]*(?:/|$))*)"
                i += 1
            else:
                result += "([^/]*)"
        else:
            result += c

        i += 1

    result += "$"

    return result


@functools.lru_cache(maxsize=256)
def _compile_glob_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(_glob_pattern_to_re(pattern))


class Pattern:
    def __init__(self, pattern: str) -> None:
        pattern = pattern.strip()

        self.only_dirs = pattern.endswith("/")

        path = PurePath(pattern)
        if path.is_absolute():
            self.pattern = path.relative_to(path.anchor).as_posix()
        else:
            self.pattern = path.as_posix()

        if "*" in self.pattern or "?" in self.pattern or "[" in self.pattern or "{" in self.pattern:
            self.re_pattern: Optional[re.Pattern[str]] = _compile_glob_pattern(self.pattern)
        else:
            self.re_pattern = None

    def matches(self, path: Union[PurePath, str, os.PathLike[str]]) -> bool:
        if isinstance(path, PurePath):
            path = path.as_posix()
        else:
            path = str(os.fspath(path))
        if self.re_pattern is None:
            return path == self.pattern

        return self.re_pattern.fullmatch(path) is not None

    def __str__(self) -> str:
        return self.pattern

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(pattern={self.pattern!r}"


def globmatches(pattern: str, path: Union[PurePath, str, os.PathLike[Any]]) -> bool:
    return Pattern(pattern).matches(path)


FILE_ATTRIBUTE_HIDDEN = 2


def _is_hidden(entry: os.DirEntry[str]) -> bool:
    if entry.name.startswith("."):
        return True

    if os.name == "nt" and (
        (not entry.is_symlink() and entry.stat().st_file_attributes & 2 != 0)  # type: ignore[attr-defined]
        or entry.name.startswith("$")
    ):
        return True

    return False


def iter_files(
    path: Union[PurePath, str, os.PathLike[str]],
    patterns: Union[Sequence[Union[Pattern, str]], Pattern, str, None] = None,
    ignore_patterns: Union[Sequence[Union[Pattern, str]], Pattern, str, None] = None,
    *,
    include_hidden: bool = False,
    absolute: bool = False,
) -> Iterator[Path]:
    if not isinstance(path, PurePath):
        path = PurePath(path or ".")

    if patterns is not None and isinstance(patterns, (str, Pattern)):
        patterns = [patterns]

    if ignore_patterns is not None and isinstance(ignore_patterns, (str, Pattern)):
        ignore_patterns = [ignore_patterns]

    yield from _iter_files_recursive_re(
        path=path,
        patterns=[] if patterns is None else [p if isinstance(p, Pattern) else Pattern(p) for p in patterns],
        ignore_patterns=[]
        if ignore_patterns is None
        else [p if isinstance(p, Pattern) else Pattern(p) for p in ignore_patterns],
        include_hidden=include_hidden,
        absolute=absolute,
        _base_path=path,
    )


def _iter_files_recursive_re(
    path: PurePath,
    patterns: Sequence[Pattern],
    ignore_patterns: Sequence[Pattern],
    include_hidden: bool,
    absolute: bool,
    _base_path: PurePath,
) -> Iterator[Path]:
    try:
        with os.scandir(path) as it:
            for f in it:
                if not include_hidden and _is_hidden(f):
                    continue

                relative_path = (path / f.name).relative_to(_base_path)

                if not ignore_patterns or not any(
                    p.matches(relative_path) and (not p.only_dirs or p.only_dirs and f.is_dir())
                    for p in cast(Iterable[Pattern], ignore_patterns)
                ):
                    if f.is_dir():
                        yield from _iter_files_recursive_re(
                            PurePath(f),
                            patterns,
                            ignore_patterns,
                            include_hidden=include_hidden,
                            absolute=absolute,
                            _base_path=_base_path,
                        )
                    if not patterns or any(
                        p.matches(relative_path) and (not p.only_dirs or p.only_dirs and f.is_dir())
                        for p in cast(Iterable[Pattern], patterns)
                    ):
                        yield Path(f).absolute() if absolute else Path(f)

    except (OSError, PermissionError):
        pass
