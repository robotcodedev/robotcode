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
from typing import TYPE_CHECKING, Callable, Iterable, Optional

import click
from robot.api import SuiteVisitor
from robot.model import Keyword as ModelKeyword
from robot.model import TestCase as ModelTestCase
from robot.model.control import For, IfBranch, Return, TryBranch, While
from robot.model.message import Message
from robot.result.model import StatusMixin
from robot.running import TestCase as RunningTestCase
from robot.running import TestSuite
from robot.utils import normalize

from robotcode.robot.utils import RF_VERSION

# Var/Group/Error only exist as model classes from RF 7.0/7.2/6.1 onwards.
# A TYPE_CHECKING import lets mypy resolve the parameter annotations on
# matrix RFs that ship the classes, while older RFs simply never call the
# corresponding `start_X` visitor methods (the items don't exist there).
if TYPE_CHECKING:
    from robot.model.control import Error, Group, Var  # type: ignore[attr-defined,unused-ignore]


# RF 7 renamed `For.variables` to `For.assign`. The legacy name remained as
# a deprecated property until RF 8 removed it. Pick the right attribute once
# at import time so the hot path inside `_BodyMatchVisitor.start_for` is a
# single attribute access.
if RF_VERSION >= (7, 0):

    def _for_assignments(for_: For) -> Iterable[str]:
        return for_.assign  # type: ignore[no-any-return]

else:

    def _for_assignments(for_: For) -> Iterable[str]:
        return for_.variables  # type: ignore[attr-defined,no-any-return,unused-ignore]


@dataclass(frozen=True)
class SearchMatcher:
    general: Callable[[Optional[str]], bool]
    tag: Callable[[Optional[str]], bool]

    def matches_body(self, body: Optional[Iterable[object]]) -> bool:
        """Walk a Robot body looking for any field that matches.

        Uses Robot's `SuiteVisitor` dispatch, which works against both the
        `robot.running` model (parse-time, used by `discover`) and the
        `robot.result` model (runtime `output.xml`, used by `results`).
        Result-tree-only fields (`.message`) are guarded with isinstance
        checks against `StatusMixin`.
        """
        if not body:
            return False
        visitor = _BodyMatchVisitor(self.general)
        for item in body:
            item.visit(visitor)  # type: ignore[attr-defined]
            if visitor.found:
                return True
        return False


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


class _BodyMatchVisitor(SuiteVisitor):
    """Walk a body looking for any field that matches the predicate.

    Sets `self.found = True` on first hit and returns `False` from every
    `start_X` so Robot's visitor stops descending. Each body-item type
    has its own `start_X`; result-tree-only fields (`.message`) are
    guarded with `isinstance(item, StatusMixin)`. Result-tree keywords
    expose the fully-qualified name via the inherited `Keyword.name`
    property (which composes `libname.kwname` on RF <7) so no version
    gate is needed there.
    """

    def __init__(self, match: Callable[[Optional[str]], bool]) -> None:
        super().__init__()
        self.match = match
        self.found = False

    def _hit(self) -> bool:
        self.found = True
        return False

    def _match_message(self, item: object) -> bool:
        # Only result-tree body items carry an inline `.message` (the
        # failure/skip text). Running-model items don't subclass
        # StatusMixin, so this short-circuits cleanly.
        return isinstance(item, StatusMixin) and bool(item.message) and self.match(item.message)

    def start_suite(self, suite: TestSuite) -> Optional[bool]:
        return False if self.found else None

    def start_test(self, test: ModelTestCase) -> Optional[bool]:
        return False if self.found else None

    def start_keyword(self, kw: ModelKeyword) -> Optional[bool]:
        if self.found:
            return False
        if self.match(kw.name):
            return self._hit()
        if any(self.match(str(a)) for a in (kw.args or ())):
            return self._hit()
        if any(self.match(str(a)) for a in (kw.assign or ())):
            return self._hit()
        if self._match_message(kw):
            return self._hit()
        return None

    def start_for(self, for_: For) -> Optional[bool]:
        if self.found:
            return False
        if any(self.match(v) for v in _for_assignments(for_)):
            return self._hit()
        if any(self.match(v) for v in (for_.values or ())):
            return self._hit()
        if self.match(for_.flavor):
            return self._hit()
        if self._match_message(for_):
            return self._hit()
        return None

    def start_while(self, while_: While) -> Optional[bool]:
        if self.found:
            return False
        if self.match(while_.condition):
            return self._hit()
        if self._match_message(while_):
            return self._hit()
        return None

    def start_if_branch(self, branch: IfBranch) -> Optional[bool]:
        if self.found:
            return False
        # `condition` is None on ELSE branches — `match` short-circuits.
        if self.match(branch.condition):
            return self._hit()
        if self._match_message(branch):
            return self._hit()
        return None

    def start_try_branch(self, branch: TryBranch) -> Optional[bool]:
        if self.found:
            return False
        if any(self.match(p) for p in (branch.patterns or ())):
            return self._hit()
        if branch.assign and self.match(branch.assign):
            return self._hit()
        if self._match_message(branch):
            return self._hit()
        return None

    def start_return(self, return_: Return) -> Optional[bool]:
        if self.found:
            return False
        if any(self.match(v) for v in (return_.values or ())):
            return self._hit()
        return None

    def start_var(self, var: "Var") -> Optional[bool]:
        if self.found:
            return False
        if self.match(var.name):
            return self._hit()
        if any(self.match(v) for v in (var.value or ())):
            return self._hit()
        return None

    def start_group(self, group: "Group") -> Optional[bool]:
        if self.found:
            return False
        if self.match(group.name):
            return self._hit()
        return None

    def start_error(self, error: "Error") -> Optional[bool]:
        if self.found:
            return False
        if any(self.match(v) for v in (error.values or ())):
            return self._hit()
        return None

    def start_message(self, msg: Message) -> Optional[bool]:
        if self.found:
            return False
        if self.match(msg.message):
            return self._hit()
        return None


class SearchModifier(SuiteVisitor):
    """Prune `suite.tests` by a `SearchMatcher` predicate.

    Same shape as `ByLongName` / `ExcludedByLongName`: tests are filtered
    in-place during `start_suite`; empty sub-suites are removed in
    `end_suite`, so the surviving tree keeps the full ancestor chain of
    any matching test.

    A test matches if any of the following matches the predicate:
    - name, full name, source path
    - documentation, template name (running model only), timeout setting
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

    def _matches(self, test: ModelTestCase) -> bool:
        if self.matcher.general(test.name) or self.matcher.general(test.longname):
            return True
        if test.source and self.matcher.general(str(test.source)):
            return True
        if self.matcher.general(test.doc):
            return True
        # `template` only exists on the running model — result-tree tests
        # don't preserve it, so guard with isinstance.
        if isinstance(test, RunningTestCase) and self.matcher.general(test.template):
            return True
        if test.timeout is not None and self.matcher.general(str(test.timeout)):
            return True
        if any(self.matcher.tag(str(t)) for t in test.tags):
            return True
        if test.has_setup and self.matcher.matches_body([test.setup]):
            return True
        if test.has_teardown and self.matcher.matches_body([test.teardown]):
            return True
        return self.matcher.matches_body(test.body)


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
