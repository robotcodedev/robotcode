import os
import re
import sys
from pathlib import Path, PurePath
from typing import Callable, Dict, Iterable, Iterator, List, NamedTuple, Optional, Reversible, Tuple, Union

from robotcode.core.utils.path import path_is_relative_to

_SEPARATORS = ["/"]
_SEPARATORS_GROUP = f"[{'|'.join(_SEPARATORS)}]"
_NO_SEPARATORS_GROUP = f"[^{'|'.join(_SEPARATORS)}]"


class _HelperCache:
    def _relative_to_path(self, path: PurePath, base_path: PurePath) -> PurePath:
        raise NotImplementedError

    def _as_posix(self, path: PurePath) -> str:
        raise NotImplementedError


class _IgnoreRule(NamedTuple):
    pattern: str
    regex: "re.Pattern[str]"
    negation: bool
    directory_only: bool
    anchored: bool
    base_path: PurePath
    source: Optional[Tuple[str, int]]

    @staticmethod
    def _relative_to_path(_helper_cache: Optional[_HelperCache], path: PurePath, base_path: PurePath) -> PurePath:
        if _helper_cache:
            return _helper_cache._relative_to_path(path, base_path)
        return path.relative_to(base_path)

    @staticmethod
    def _as_posix(_helper_cache: Optional[_HelperCache], path: PurePath) -> str:
        if _helper_cache:
            return _helper_cache._as_posix(path)
        return path.as_posix()

    def __str__(self) -> str:
        return self.pattern

    def __repr__(self) -> str:
        return f"IgnoreRule('{self.pattern}')"

    def matches(
        self, normalized_path: PurePath, is_dir: Optional[bool] = None, _helper_cache: Optional[_HelperCache] = None
    ) -> bool:
        if is_dir is None:
            is_dir = Path(normalized_path).is_dir()

        if self.directory_only and not is_dir:
            return False

        if self.base_path:
            try:
                rel_path = self._as_posix(
                    _helper_cache, self._relative_to_path(_helper_cache, normalized_path, self.base_path)
                )
            except ValueError:
                return False
        else:
            rel_path = self._as_posix(_helper_cache, normalized_path)

        if self.negation and is_dir:
            rel_path += "/"
        if rel_path.startswith("./"):
            rel_path = rel_path[2:]
        if self.regex.search(rel_path):
            return True
        return False


class IgnoreSpec(_HelperCache):
    def __init__(self, rules: Reversible[_IgnoreRule]):
        self.rules = rules
        self.negation = any(r.negation for r in rules)

        self._reversed_rules = list(reversed(rules))

        self._relative_path_cache: Dict[Tuple[PurePath, PurePath], PurePath] = {}
        self._posix_path_cache: Dict[PurePath, str] = {}

    def _relative_to_path(self, path: PurePath, base_path: PurePath) -> PurePath:
        key = (path, base_path)

        if key in self._relative_path_cache:
            return self._relative_path_cache[key]

        result = path.relative_to(base_path)
        self._relative_path_cache[key] = result
        return result

    def _as_posix(self, path: PurePath) -> str:
        if path in self._posix_path_cache:
            return self._posix_path_cache[path]

        result = path.as_posix()
        self._posix_path_cache[path] = result
        return result

    def matches(self, path: "os.PathLike[str]") -> bool:
        abs_path = Path(os.path.abspath(path))
        pure_file_path = PurePath(abs_path)
        is_dir = abs_path.is_dir()

        if not self.negation:
            return any(r.matches(pure_file_path, is_dir, self) for r in self.rules)

        for rule in self._reversed_rules:
            if rule.matches(pure_file_path, is_dir, self):
                return not rule.negation

        return False

    def __add__(self, other: "IgnoreSpec") -> "IgnoreSpec":
        return IgnoreSpec(tuple(self.rules) + tuple(other.rules))

    @classmethod
    def from_list(cls, rules: Iterable[str], base_dir: "os.PathLike[str]") -> "IgnoreSpec":
        return IgnoreSpec(
            [p for p in [cls._rule_from_pattern(r, PurePath(Path(os.path.abspath(base_dir)))) for r in rules] if p]
        )

    @classmethod
    def from_gitignore(cls, path: "os.PathLike[str]") -> "IgnoreSpec":
        rules = []
        gitignore_file = Path(path)
        if gitignore_file.is_file():
            base_dir = PurePath(Path(os.path.abspath(path)).parent)
            for line, pattern in enumerate(gitignore_file.read_text("utf-8").splitlines()):
                rule = cls._rule_from_pattern(pattern, base_path=base_dir, source=(str(path), line))
                if rule:
                    rules.append(rule)

        return IgnoreSpec(rules)

    @classmethod
    def _rule_from_pattern(
        cls, pattern: str, base_path: PurePath, source: Optional[Tuple[str, int]] = None
    ) -> Optional[_IgnoreRule]:

        orig_pattern = pattern

        if pattern.strip() == "" or pattern[0] == "#":
            return None

        if pattern[0] == "!":
            negation = True
            pattern = pattern[1:]
        else:
            negation = False

        pattern = re.sub(r"([^/])\*{2,}", r"\1*", pattern)
        pattern = re.sub(r"\*{2,}([^/])", r"*\1", pattern)

        if pattern.rstrip() == "/":
            return None

        directory_only = pattern[-1] == "/"

        anchored = "/" in pattern[:-1]
        if pattern[0] == "/":
            pattern = pattern[1:]
        if pattern[0] == "*" and len(pattern) >= 2 and pattern[1] == "*":
            pattern = pattern[2:]
            anchored = False
        if pattern[0] == "/":
            pattern = pattern[1:]
        if pattern[-1] == "/":
            pattern = pattern[:-1]

        if pattern[0] == "\\" and pattern[1] in ("#", "!"):
            pattern = pattern[1:]

        i = len(pattern) - 1
        striptrailingspaces = True
        while i > 1 and pattern[i] == " ":
            if pattern[i - 1] == "\\":
                pattern = pattern[: i - 1] + pattern[i:]
                i = i - 1
                striptrailingspaces = False
            else:
                if striptrailingspaces:
                    pattern = pattern[:i]
            i = i - 1
        regex = cls._fnmatch_pathname_to_regex(pattern, directory_only, negation, anchored=bool(anchored))

        return _IgnoreRule(
            pattern=orig_pattern,
            regex=re.compile(regex),
            negation=negation,
            directory_only=directory_only,
            anchored=anchored,
            base_path=base_path,
            source=source,
        )

    @classmethod
    def _fnmatch_pathname_to_regex(
        cls, pattern: str, directory_only: bool, negation: bool, anchored: bool = False
    ) -> str:
        i, n = 0, len(pattern)

        res = []
        while i < n:
            c = pattern[i]
            i += 1
            if c == "*":
                try:
                    if pattern[i] == "*":
                        i += 1
                        if i < n and pattern[i] == "/":
                            i += 1
                            res.append(f"(.*{_SEPARATORS_GROUP})?")
                        else:
                            res.append(".*")
                    else:
                        res.append(_NO_SEPARATORS_GROUP + "*")
                except IndexError:
                    res.append(_NO_SEPARATORS_GROUP + "*")
            elif c == "?":
                res.append(_NO_SEPARATORS_GROUP)
            elif c == "/":
                res.append(_SEPARATORS_GROUP)
            elif c == "[":
                j = i
                if j < n and pattern[j] == "!":
                    j += 1
                if j < n and pattern[j] == "]":
                    j += 1
                while j < n and pattern[j] != "]":
                    j += 1
                if j >= n:
                    res.append("\\[")
                else:
                    stuff = pattern[i:j].replace("\\", "\\\\").replace("/", "")
                    i = j + 1
                    if stuff[0] == "!":
                        stuff = "^" + stuff[1:]
                    elif stuff[0] == "^":
                        stuff = "\\" + stuff
                    res.append(f"[{stuff}]")
            else:
                res.append(re.escape(c))
        if anchored:
            res.insert(0, "^")
        else:
            res.insert(0, f"(^|{_SEPARATORS_GROUP})")
        if not directory_only:
            res.append("$")
        elif directory_only and negation:
            res.append("/$")
        else:
            res.append("($|\\/)")
        return "".join(res)


DEFAULT_SPEC_RULES = [".git/", ".svn/", "CVS/"]

GIT_IGNORE_FILE = ".gitignore"
ROBOT_IGNORE_FILE = ".robotignore"


_FILE_ATTRIBUTE_HIDDEN = 2


def _is_hidden(entry: Path) -> bool:
    if entry.name.startswith("."):
        return True

    if sys.platform == "win32" and (
        (not entry.is_symlink() and entry.stat().st_file_attributes & _FILE_ATTRIBUTE_HIDDEN != 0)
        or entry.name.startswith("$")
    ):
        return True

    return False


def iter_files(
    paths: Union[Path, Iterable[Path]],
    root: Optional[Path] = None,
    ignore_files: Iterable[str] = [GIT_IGNORE_FILE],
    include_hidden: bool = True,
    parent_spec: Optional[IgnoreSpec] = None,
    verbose_callback: Optional[Callable[[str], None]] = None,
    verbose_trace: bool = False,
) -> Iterator[Path]:
    if isinstance(paths, Path):
        paths = [paths]

    for path in paths:
        yield from _iter_files(
            Path(os.path.abspath(path)),
            root=Path(os.path.abspath(root)) if root is not None else root,
            ignore_files=ignore_files,
            include_hidden=include_hidden,
            parent_spec=parent_spec,
            verbose_callback=verbose_callback,
            verbose_trace=verbose_trace,
        )


def _iter_files(
    path: Path,
    root: Optional[Path] = None,
    ignore_files: Iterable[str] = [GIT_IGNORE_FILE],
    include_hidden: bool = True,
    parent_spec: Optional[IgnoreSpec] = None,
    verbose_callback: Optional[Callable[[str], None]] = None,
    verbose_trace: bool = False,
) -> Iterator[Path]:
    if verbose_callback is not None and verbose_trace:
        verbose_callback(f"iter_files: {path}")

    if root is None:
        root = path if path.is_dir() else path.parent

    if parent_spec is None:
        parent_spec = IgnoreSpec.from_list(DEFAULT_SPEC_RULES, path)

        if path_is_relative_to(path, root):
            parents: List[Path] = []
            p = path if path.is_dir() else path.parent
            while True:
                p = p.parent

                if p < root:
                    break

                parents.insert(0, p)

            for p in parents:
                ignore_file = next((p / f for f in ignore_files if (p / f).is_file()), None)

                if ignore_file is not None:
                    if verbose_callback is not None:
                        verbose_callback(f"using ignore file: '{ignore_file}'")
                    parent_spec = parent_spec + IgnoreSpec.from_gitignore(ignore_file)
                    ignore_files = [ignore_file.name]

    ignore_file = next((path / f for f in ignore_files if (path / f).is_file()), None)

    if ignore_file is not None:
        if verbose_callback is not None:
            verbose_callback(f"using ignore file: '{ignore_file}'")
        spec = parent_spec + IgnoreSpec.from_gitignore(ignore_file)
        ignore_files = [ignore_file.name]
    else:
        spec = parent_spec

    if not path.is_dir():
        if spec is not None and spec.matches(path):
            return
        yield path
        return

    for p in path.iterdir():
        if not include_hidden and _is_hidden(p):
            continue

        if spec is not None and spec.matches(p):
            continue

        if p.is_dir():
            yield from _iter_files(
                p,
                ignore_files=ignore_files,
                include_hidden=include_hidden,
                parent_spec=spec,
                verbose_callback=verbose_callback,
                verbose_trace=verbose_trace,
            )
        elif p.is_file():
            yield p
