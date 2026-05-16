"""Shared search infrastructure for the runner CLI subcommands.

The `--search` / `--search-regex` semantics live here so both `results` and
`discover` can share them. Each matcher carries two predicates:

- `general` — plain substring / regex predicate, used for names, paths,
  messages, keyword args …
- `tag` — applies Robot's tag normalisation (lowercase, no whitespace,
  no underscores) on both sides before comparing, so `bug 123` matches a
  test tagged `bug_123` and vice versa.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

import click
from robot.api import SuiteVisitor
from robot.running import TestCase, TestSuite
from robot.utils import normalize


@dataclass(frozen=True)
class SearchMatcher:
    general: Callable[[Optional[str]], bool]
    tag: Callable[[Optional[str]], bool]

    def matches_body(self, body: Any) -> bool:
        """Recurse through a Robot test body looking for any match.

        Works against both the `robot.running` model (parse-time, used by
        `discover`) and the `robot.result` model (runtime `output.xml`,
        used by `results`) via duck-typing.
        """
        return _body_matches(body, self.general)


def make_search_matcher(substring: Optional[str], regex: Optional[str]) -> Optional[SearchMatcher]:
    """Compile a search predicate once.

    Exactly one of `substring` / `regex` may be set. `substring` is matched
    case-insensitively as a plain `in` check. `regex` is matched without any
    case-folding by default — use `(?i)pattern` to make a regex
    case-insensitive. Returns `None` if neither is given.
    """
    if substring and regex:
        raise click.UsageError("--search and --search-regex are mutually exclusive.")
    if substring:
        needle = substring.lower()
        needle_norm = normalize(substring, ignore="_")

        def general(s: Optional[str]) -> bool:
            return bool(s and needle in s.lower())

        def tag(s: Optional[str]) -> bool:
            return bool(s and needle_norm in normalize(s, ignore="_"))

        return SearchMatcher(general=general, tag=tag)
    if regex:
        try:
            rx = re.compile(regex)
        except re.error as e:
            raise click.UsageError(f"--search-regex: invalid pattern: {e}") from e

        def general(s: Optional[str]) -> bool:
            return bool(s and rx.search(s))

        def tag(s: Optional[str]) -> bool:
            return bool(s and rx.search(normalize(s, ignore="_")))

        return SearchMatcher(general=general, tag=tag)
    return None


def make_highlighter(substring: Optional[str], regex: Optional[str]) -> Optional[Callable[[str], str]]:
    """Return a `highlight(text) -> styled_text` function, or None when no pattern.

    Wraps each match in a yellow-on-black bold span via `click.style`.
    Substring matches are highlighted case-insensitively (matching the
    `--search` semantics); regex patterns are honoured as the user wrote
    them so `(?i)` opts into case-insensitive highlighting too.
    """
    if not substring and not regex:
        return None
    if regex:
        flags = 0
        raw = regex
    else:
        flags = re.IGNORECASE
        raw = re.escape(substring or "")
    try:
        rx = re.compile(raw, flags)
    except re.error:
        return None

    def highlight(text: str) -> str:
        if not text:
            return text
        return rx.sub(lambda m: click.style(m.group(0), fg="black", bg="yellow", bold=True), text)

    return highlight


def _body_matches(body: Any, match: Callable[[Optional[str]], bool]) -> bool:
    """Recurse through a Robot body iterable looking for any match.

    Works against both the `robot.running` model (parse-time, used by
    `discover`) and the `robot.result` model (runtime `output.xml`, used
    by `results`) via duck-typing. Result-tree-only fields (`message`,
    MESSAGE-type items) simply return None on a running-model item.
    """
    if not body:
        return False
    for item in body:
        t = getattr(item, "type", "") or ""

        # MESSAGE items: only exist in the result tree (log records).
        if t == "MESSAGE" or (not t and hasattr(item, "level") and hasattr(item, "message")):
            if match(getattr(item, "message", None)):
                return True
            continue

        # Result-tree keywords/branches carry an inline `.message`
        # (the failure/skip text). Running-model items have no such
        # attribute, so getattr returns None and `match` short-circuits.
        if match(getattr(item, "message", None)):
            return True

        if t in ("KEYWORD", "SETUP", "TEARDOWN"):
            # RF <7 result-tree splits the keyword into `kwname` (short)
            # and `libname` (owner). RF 7+ result-tree uses `name` +
            # `owner`. Running model has just `name` (already qualified
            # if needed). Try `kwname` first, then fall back to
            # `name`/`owner`.
            kwname = getattr(item, "kwname", None)
            full: Optional[str]
            if kwname is not None:
                short = str(kwname)
                libname = getattr(item, "libname", None)
                full = f"{libname}.{short}" if libname else short
            else:
                name = getattr(item, "name", None)
                owner = getattr(item, "owner", None)
                full = f"{owner}.{name}" if owner and name else name
            if match(full):
                return True
            if any(match(a) for a in (getattr(item, "args", None) or [])):
                return True
            if any(match(a) for a in (getattr(item, "assign", None) or [])):
                return True
        elif t == "FOR":
            # `For.assign` is the modern name (RF 7+); `For.variables` is
            # the legacy one, deprecated and removed in RF 8.
            for_vars = getattr(item, "assign", None) or getattr(item, "variables", None)
            if any(match(v) for v in (for_vars or [])):
                return True
            if any(match(v) for v in (getattr(item, "values", None) or [])):
                return True
            if match(getattr(item, "flavor", None)):
                return True
        elif t in ("WHILE", "IF", "ELSE IF"):
            if match(getattr(item, "condition", None)):
                return True
        elif t == "VAR":
            if match(getattr(item, "name", None)):
                return True
            if any(match(v) for v in (getattr(item, "value", None) or [])):
                return True
        elif t == "RETURN":
            if any(match(v) for v in (getattr(item, "values", None) or [])):
                return True
        elif t == "EXCEPT":
            if any(match(p) for p in (getattr(item, "patterns", None) or [])):
                return True
            ex_assign = getattr(item, "assign", None)
            if ex_assign and match(ex_assign):
                return True
        elif t == "GROUP":
            if match(getattr(item, "name", None)):
                return True

        sub = getattr(item, "body", None)
        if sub and _body_matches(sub, match):
            return True
    return False


class SearchModifier(SuiteVisitor):
    """Prune `suite.tests` by a `SearchMatcher` predicate.

    Same shape as `ByLongName` / `ExcludedByLongName`: tests are filtered
    in-place during `start_suite`; empty sub-suites are removed in
    `end_suite`, so the surviving tree keeps the full ancestor chain of
    any matching test.

    A test matches if any of the following matches the predicate:
    - name, full name, source path
    - documentation, template name, timeout setting
    - any of its tags (with Robot's tag normalisation)
    - any keyword name, keyword argument, assigned variable, FOR/WHILE
      condition or VAR/RETURN/EXCEPT/GROUP element inside the test body,
      setup or teardown
    """

    def __init__(self, matcher: SearchMatcher) -> None:
        super().__init__()
        self.matcher = matcher

    def start_suite(self, suite: TestSuite) -> None:
        suite.tests = [t for t in suite.tests if self._matches(t)]

    def end_suite(self, suite: TestSuite) -> None:
        suite.suites = [s for s in suite.suites if s.test_count > 0]

    def _matches(self, test: TestCase) -> bool:
        if self.matcher.general(test.name) or self.matcher.general(test.longname):
            return True
        if test.source and self.matcher.general(str(test.source)):
            return True
        if self.matcher.general(getattr(test, "doc", None)):
            return True
        if self.matcher.general(getattr(test, "template", None)):
            return True
        if self.matcher.general(getattr(test, "timeout", None)):
            return True
        if any(self.matcher.tag(str(t)) for t in test.tags):
            return True
        setup = getattr(test, "setup", None)
        if setup and self.matcher.matches_body([setup]):
            return True
        teardown = getattr(test, "teardown", None)
        if teardown and self.matcher.matches_body([teardown]):
            return True
        return self.matcher.matches_body(getattr(test, "body", None))


_STATUS_ALIASES = {
    "pass": "PASS",
    "fail": "FAIL",
    "skip": "SKIP",
    "not-run": "NOT RUN",
    "not_run": "NOT RUN",
}


class ByStatus(SuiteVisitor):
    """Prune `suite.tests` to those whose status is in the wanted set.

    Robot Framework has no native filter equivalent (its `--include`/
    `--exclude` are tag-based; `suite.filter` doesn't accept a status
    selector), so we apply this as a post-step on the already-loaded
    result tree. Same shape as `ByLongName`/`SearchModifier` so it slots
    into the same `ModelModifier` pipeline.
    """

    def __init__(self, *statuses: str) -> None:
        super().__init__()
        self.wanted = {_STATUS_ALIASES.get(s.lower(), s.upper()) for s in statuses}

    def start_suite(self, suite: TestSuite) -> None:
        if self.wanted:
            suite.tests = [t for t in suite.tests if t.status in self.wanted]

    def end_suite(self, suite: TestSuite) -> None:
        suite.suites = [s for s in suite.suites if s.test_count > 0]
