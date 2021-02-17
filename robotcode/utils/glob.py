from typing import Union
import os
import re
from pathlib import Path


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

    def matches(self, path: Union[Path, str, os.PathLike[str]]) -> bool:
        return self._re_pattern.fullmatch(str(Path(path)).replace(os.sep, "/")) is not None

    def __str__(self) -> str:
        return self.pattern

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(pattern={repr(self.pattern)}"


def globmatches(pattern: str, path: Union[Path, str, os.PathLike[str]]) -> bool:
    return Pattern(pattern).matches(path)
