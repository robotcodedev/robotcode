from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Generator, Iterable, Sequence, Union, cast


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


class Pattern:
    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        self._re_pattern = re.compile(_glob_pattern_to_re(pattern))

    def matches(self, path: Union[Path, str, os.PathLike[Any]]) -> bool:
        if not isinstance(path, Path):
            path = Path(path)
        return self._re_pattern.fullmatch(str(path).replace(os.sep, "/")) is not None

    def __str__(self) -> str:
        return self.pattern

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(pattern={repr(self.pattern)}"


def globmatches(pattern: str, path: Union[Path, str, os.PathLike[Any]]) -> bool:
    return Pattern(pattern).matches(path)


def iter_files(
    path: Union[Path, str, os.PathLike[str]],
    patterns: Union[Sequence[Union[Pattern, str]], Pattern, str, None] = None,
    ignore_patterns: Union[Sequence[Union[Pattern, str]], Pattern, str, None] = None,
    *,
    absolute: bool = False,
    _base_path: Union[Path, str, os.PathLike[str], None] = None,
) -> Generator[Path, None, None]:
    if not isinstance(path, Path):
        path = Path(path or ".")

    if _base_path is None:
        _base_path = path
    else:
        if not isinstance(_base_path, Path):
            path = Path(_base_path)

    if patterns is not None and isinstance(patterns, (str, Pattern)):
        patterns = [patterns]
    if patterns is not None:
        patterns = list(map(lambda p: p if isinstance(p, Pattern) else Pattern(p), patterns))

    if ignore_patterns is not None and isinstance(ignore_patterns, (str, Pattern)):
        ignore_patterns = [ignore_patterns]
    if ignore_patterns is not None:
        ignore_patterns = list(map(lambda p: p if isinstance(p, Pattern) else Pattern(p), ignore_patterns))

    try:
        for f in path.iterdir():
            if ignore_patterns is None or not any(
                p.matches(f.relative_to(_base_path)) for p in cast(Iterable[Pattern], ignore_patterns)
            ):
                if f.is_dir():
                    for e in iter_files(f, patterns, ignore_patterns, absolute=absolute, _base_path=_base_path):
                        yield e
                elif patterns is None or any(
                    p.matches(str(f.relative_to(_base_path))) for p in cast(Iterable[Pattern], patterns)
                ):
                    yield f.absolute() if absolute else f
    except PermissionError:
        pass
